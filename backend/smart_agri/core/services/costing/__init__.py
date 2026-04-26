from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import OperationalError
from django.utils import timezone

from smart_agri.core.models.settings import LaborRate
from smart_agri.finance.models import CostConfiguration

from .calculator import CostCalculator
from .policy import CostPolicy
from .service import COSTING_STRICT_MODE, CostService

import logging
logger = logging.getLogger(__name__)

# Backward Compatibility Aliases
calculate_activity_cost = CostService.calculate_activity_cost
calculate_bulk_costs = CostService.calculate_bulk_costs
calculate_daily_labor_cost = CostCalculator.calculate_daily_labor_cost
to_decimal = CostPolicy.to_decimal


class CostingValidationError(ValidationError, ValueError):
    """Compatibility exception for legacy tests expecting different exception bases."""
    pass


def _raise_or_default(exc: Exception, strict: bool):
    if strict:
        raise CostingValidationError(str(exc))
    return Decimal("0")


def _get_overhead_rate(farm_id, strict=True):
    if strict and not farm_id:
        raise CostingValidationError("نشاط يتيم: لا يمكن احتساب التكاليف غير المباشرة بدون نطاق مزرعة.")

    if strict:
        config = (
            CostConfiguration.objects.filter(
                farm_id=farm_id,
                deleted_at__isnull=True,
            )
            .only("id", "overhead_rate_per_hectare")
            .first()
        )
        if not config or config.overhead_rate_per_hectare is None:
            raise CostingValidationError(f"لا يوجد CostConfiguration للمزرعة {farm_id}.")
    try:
        return CostPolicy.get_overhead_rate(farm_id)
    except (ValidationError, CostConfiguration.DoesNotExist, OperationalError) as exc:
        if strict:
            raise CostingValidationError(f"لا يوجد CostConfiguration للمزرعة {farm_id}: {exc}")
        return Decimal("0")


def _get_labor_daily_rate(farm_id, strict=True):
    return _get_labor_rate(farm_id, strict=strict)


def _get_labor_rate(farm_id, strict=True):
    try:
        return CostPolicy.get_labor_daily_rate(farm_id)
    except (ValidationError, LaborRate.DoesNotExist):
        try:
            rate = (
                LaborRate.objects.filter(
                    farm_id=farm_id,
                    effective_date__lte=timezone.now().date(),
                    deleted_at__isnull=True,
                )
                .order_by("-effective_date")
                .first()
            )
            if rate and rate.cost_per_hour is not None:
                return rate.cost_per_hour
        except (OperationalError, ValidationError) as exc:
            logger.warning("LaborRate DB fallback failed for farm %s: %s", farm_id, exc)
        return _raise_or_default(
            CostingValidationError(f"خطأ: لا يوجد معدل عمالة نشط للمزرعة {farm_id}."),
            strict,
        )


def _get_machine_rate(asset_id, strict=True):
    try:
        return CostPolicy.get_machine_rate(asset_id)
    except (ValidationError, OperationalError):
        if strict:
            raise CostingValidationError(f"لا يوجد معدل آلة للأصل {asset_id}.")
        return Decimal("0")


__all__ = [
    "CostService",
    "CostPolicy",
    "COSTING_STRICT_MODE",
    "calculate_daily_labor_cost",
    "_get_overhead_rate",
    "_get_labor_daily_rate",
    "_get_labor_rate",
    "_get_machine_rate",
    "to_decimal",
    "calculate_activity_cost",
    "calculate_bulk_costs",
]
