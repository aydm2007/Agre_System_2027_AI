import logging
from decimal import Decimal, InvalidOperation
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import OperationalError, ProgrammingError
from django.utils import timezone

from smart_agri.core.models.settings import LaborRate, MachineRate
from smart_agri.finance.models import CostConfiguration

logger = logging.getLogger(__name__)


class CostPolicy:
    """Policy layer for financial calculations and rate retrieval."""

    @staticmethod
    def to_decimal(value, field_name="Value") -> Decimal:
        if value is None:
            raise ValidationError(f"خطأ مالي حرج: الحقل {field_name} مطلوب.")
        if isinstance(value, float):
            raise ValidationError(
                f"خطأ مالي حرج: استخدام float ممنوع في {field_name}. استخدم Decimal أو نصًا رقميًا."
            )
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            raise ValidationError(f"خطأ مالي حرج: قيمة غير صالحة في {field_name}.")

    @staticmethod
    def get_overhead_rate(farm_id: Optional[int]) -> Decimal:
        if not farm_id:
            raise ValidationError(
                "خطأ تكامل مالي: لا يمكن احتساب التكاليف غير المباشرة بدون نطاق مزرعة."
            )

        try:
            config = CostConfiguration.objects.only("overhead_rate_per_hectare").get(
                farm_id=farm_id,
                deleted_at__isnull=True,
            )
        except CostConfiguration.DoesNotExist:
            raise ValidationError(f"لا يوجد إعداد تكلفة (CostConfiguration) للمزرعة {farm_id}.")

        if config.overhead_rate_per_hectare is None:
            raise ValidationError(f"معدل التكاليف غير المباشرة غير محدد للمزرعة {farm_id}.")

        return Decimal(config.overhead_rate_per_hectare)

    @staticmethod
    def get_labor_daily_rate(farm_id: Optional[int]) -> Decimal:
        if not farm_id:
            raise ValidationError("لا يمكن تحديد معدل العمالة بدون نطاق مزرعة.")

        rate = (
            LaborRate.objects.filter(
                farm_id=farm_id,
                effective_date__lte=timezone.now().date(),
                deleted_at__isnull=True,
            )
            .order_by("-effective_date")
            .first()
        )
        if not rate:
            raise ValidationError(f"لا يوجد معدل عمالة نشط للمزرعة {farm_id}.")

        if hasattr(rate, "daily_rate") and rate.daily_rate is not None:
            return Decimal(rate.daily_rate)
        if rate.cost_per_hour is not None:
            return Decimal(rate.cost_per_hour)
        raise ValidationError(f"ERR_DAILY_RATE_REQUIRED: معدل الأجر اليومي للعمالة مفقود للمزرعة {farm_id}.")

    @staticmethod
    def get_machine_rate(asset_id: Optional[int]) -> Decimal:
        if not asset_id:
            return Decimal("0")

        try:
            machine_rate = MachineRate.objects.select_for_update().select_related("asset").get(
                asset_id=asset_id,
                deleted_at__isnull=True,
            )
        except MachineRate.DoesNotExist:
            raise ValidationError(f"معدل تشغيل المعدة مفقود للأصل {asset_id}.")
        except (OperationalError, ProgrammingError) as exc:
            logger.error("Critical DB error fetching MachineRate: %s", exc)
            raise

        if hasattr(machine_rate, "daily_rate") and machine_rate.daily_rate is not None:
            return Decimal(machine_rate.daily_rate)
        if machine_rate.cost_per_hour is None:
            raise ValidationError(f"قيمة معدل تشغيل المعدة فارغة للأصل {asset_id}.")
        return Decimal(machine_rate.cost_per_hour)
