from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from smart_agri.core.api.permissions import _ensure_user_has_farm_access
from smart_agri.core.models.farm import Farm, Location
from smart_agri.core.models.hr import Employee, Timesheet
from smart_agri.inventory.models import Item, ItemInventory, StockMovement


class QROperationService:
    """
    Domain service for QR operations.
    View layer must remain orchestration-only and never write directly.
    """

    ITEM_PREFIX = "ITEM"
    EMP_PREFIX = "EMP"

    @staticmethod
    def _split_qr(qr_string: str) -> tuple[str, str]:
        if not qr_string or ":" not in qr_string:
            raise ValidationError({"detail": "QR Code غير صالح."})
        prefix, entity_id = qr_string.split(":", 1)
        return prefix, entity_id

    @staticmethod
    def resolve(*, actor, qr_string: str, farm_id=None) -> dict:
        prefix, entity_id = QROperationService._split_qr(qr_string)

        try:
            entity_pk = int(entity_id)
        except (TypeError, ValueError) as exc:
            raise ValidationError({"detail": "صيغة العنصر في QR غير صالحة."}) from exc

        if prefix == QROperationService.ITEM_PREFIX:
            item = Item.objects.filter(pk=entity_pk).first()
            if item is None:
                raise ValidationError({"detail": "العنصر غير موجود في النظام."})

            current_qty = Decimal("0")
            if farm_id:
                _ensure_user_has_farm_access(actor, farm_id)
                current_qty = (
                    ItemInventory.objects.filter(item=item, farm_id=farm_id)
                    .aggregate(total=Coalesce(Sum("qty"), Decimal("0")))
                    .get("total", Decimal("0"))
                )

            return {
                "status": "success",
                "type": "item",
                "id": item.id,
                "name": item.name,
                "uom": item.uom,
                "current_qty": str(current_qty),
            }

        if prefix == QROperationService.EMP_PREFIX:
            emp = Employee.objects.filter(pk=entity_pk).first()
            if emp is None:
                raise ValidationError({"detail": "الموظف غير موجود في النظام."})
            _ensure_user_has_farm_access(actor, emp.farm_id)
            return {
                "status": "success",
                "type": "employee",
                "id": emp.id,
                "name": f"{emp.first_name} {emp.last_name}",
                "role": emp.get_role_display(),
            }

        raise ValidationError({"detail": "نوع QR غير مدعوم."})

    @staticmethod
    def execute(
        *,
        actor,
        qr_string: str,
        action_type: str,
        farm_id=None,
        location_id=None,
        amount: Decimal | str | int | float = Decimal("0"),
        note: str = "",
        idempotency_key: str,
    ) -> dict:
        if not idempotency_key:
            raise ValidationError({"detail": "X-Idempotency-Key is required."})

        prefix, entity_id = QROperationService._split_qr(qr_string)
        try:
            entity_pk = int(entity_id)
        except (TypeError, ValueError) as exc:
            raise ValidationError({"detail": "صيغة العنصر في QR غير صالحة."}) from exc

        try:
            amount_decimal = Decimal(str(amount))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValidationError({"detail": "قيمة الكمية غير صالحة."}) from exc

        with transaction.atomic():
            if prefix == QROperationService.ITEM_PREFIX and action_type in {"consume", "add"}:
                if not farm_id:
                    raise ValidationError({"detail": "معرف المزرعة مطلوب لحركة المخزون."})
                if amount_decimal <= 0:
                    raise ValidationError({"detail": "الكمية يجب أن تكون أكبر من الصفر."})

                _ensure_user_has_farm_access(actor, farm_id)
                item = Item.objects.filter(pk=entity_pk).first()
                farm = Farm.objects.filter(pk=farm_id).first()
                if item is None or farm is None:
                    raise ValidationError({"detail": "مرجع عنصر/مزرعة غير صالح."})

                location = None
                if location_id:
                    location = Location.objects.filter(pk=location_id).first()
                    if location is None or location.farm_id != farm.id:
                        raise ValidationError({"detail": "الموقع غير صالح أو خارج نطاق المزرعة."})

                # Lock current inventory rows for deterministic concurrent mutations.
                list(
                    ItemInventory.objects.select_for_update().filter(
                        item_id=item.id,
                        farm_id=farm.id,
                    )[:1]
                )

                qty_delta = -amount_decimal if action_type == "consume" else amount_decimal
                StockMovement.objects.create(
                    farm=farm,
                    item=item,
                    location=location,
                    qty_delta=qty_delta,
                    ref_type="qr_scan",
                    ref_id=str(idempotency_key),
                    note=note or "",
                )
                return {"message": f"تم تسجيل الحركة ({action_type}) بنجاح."}

            if prefix == QROperationService.EMP_PREFIX and action_type == "attendance":
                employee = Employee.objects.filter(pk=entity_pk).first()
                if employee is None:
                    raise ValidationError({"detail": "الموظف غير موجود في النظام."})
                _ensure_user_has_farm_access(actor, employee.farm_id)
                Timesheet.objects.create(
                    employee=employee,
                    date=timezone.localdate(),
                    surrah_count=Decimal("1.00"),
                    is_approved=False,
                )
                return {"message": "تم تحضير العامل بنجاح بنظام الصرة."}

            raise ValidationError({"detail": "إجراء غير متطابق مع نوع الـ QR."})
