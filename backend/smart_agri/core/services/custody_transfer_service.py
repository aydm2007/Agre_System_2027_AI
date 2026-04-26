from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Iterable, Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from smart_agri.core.models import AuditLog, CustodyTransfer, ItemInventory
from smart_agri.core.models.farm import Farm, Location
from smart_agri.core.models.settings import Supervisor
from smart_agri.core.services.inventory_service import InventoryService
from smart_agri.inventory.models import Item


class CustodyTransferService:
    IN_TRANSIT_CODE = "CUSTODY-IN-TRANSIT"
    CUSTODY_CODE_PREFIX = "CUSTODY"

    @staticmethod
    def _as_decimal(value, *, field_name: str) -> Decimal:
        if isinstance(value, float):
            raise ValidationError({field_name: "استخدام float ممنوع. أرسل القيمة كنص أو Decimal."})
        try:
            quantity = Decimal(str(value))
        except (ArithmeticError, TypeError, ValueError) as exc:
            raise ValidationError({field_name: f"قيمة رقمية غير صالحة: {value}"}) from exc
        if quantity <= 0:
            raise ValidationError({field_name: "يجب أن تكون الكمية أكبر من صفر."})
        return quantity.quantize(Decimal("0.001"))

    @staticmethod
    def _get_or_create_in_transit_location(*, farm: Farm) -> Location:
        location, _ = Location.objects.get_or_create(
            farm=farm,
            code=CustodyTransferService.IN_TRANSIT_CODE,
            defaults={
                "name": "عهدة قيد التسليم",
                "type": "Transit",
            },
        )
        if location.type != "Transit":
            location.type = "Transit"
            location.save(update_fields=["type"])
        return location

    @staticmethod
    def _get_or_create_custody_location(*, farm: Farm, supervisor: Supervisor) -> Location:
        code = f"{CustodyTransferService.CUSTODY_CODE_PREFIX}-{supervisor.id}"
        location, _ = Location.objects.get_or_create(
            farm=farm,
            code=code,
            defaults={
                "name": f"عهدة المشرف {supervisor.name}",
                "type": "Custody",
            },
        )
        desired_name = f"عهدة المشرف {supervisor.name}"
        update_fields = []
        if location.type != "Custody":
            location.type = "Custody"
            update_fields.append("type")
        if location.name != desired_name:
            location.name = desired_name
            update_fields.append("name")
        if update_fields:
            location.save(update_fields=update_fields)
        return location

    @staticmethod
    def _append_audit(*, actor, farm: Farm, action: str, transfer: CustodyTransfer, payload: dict, reason: str) -> None:
        AuditLog.objects.create(
            actor=actor,
            farm=farm,
            action=action,
            model="CustodyTransfer",
            object_id=str(transfer.pk),
            new_payload=payload,
            reason=reason,
        )

    @staticmethod
    def get_supervisor_custody_location(*, farm: Farm, supervisor: Supervisor) -> Location:
        return CustodyTransferService._get_or_create_custody_location(farm=farm, supervisor=supervisor)

    @staticmethod
    def get_item_custody_balance(*, farm: Farm, supervisor: Supervisor, item: Item) -> Decimal:
        custody_location = CustodyTransferService.get_supervisor_custody_location(
            farm=farm,
            supervisor=supervisor,
        )
        return InventoryService.get_stock_level(farm=farm, item=item, location=custody_location).quantize(
            Decimal("0.001")
        )

    @staticmethod
    def get_outstanding_open_balance(*, farm: Farm, supervisor: Supervisor, item: Item) -> Decimal:
        accepted_total = (
            CustodyTransfer.objects.filter(
                farm=farm,
                supervisor=supervisor,
                item=item,
                deleted_at__isnull=True,
                status__in=[
                    CustodyTransfer.STATUS_ACCEPTED,
                    CustodyTransfer.STATUS_PARTIALLY_CONSUMED,
                    CustodyTransfer.STATUS_EXPIRED_REVIEW,
                ],
            ).aggregate(total=Sum("accepted_qty")).get("total")
            or Decimal("0")
        )
        returned_total = (
            CustodyTransfer.objects.filter(
                farm=farm,
                supervisor=supervisor,
                item=item,
                deleted_at__isnull=True,
                status__in=[
                    CustodyTransfer.STATUS_ACCEPTED,
                    CustodyTransfer.STATUS_PARTIALLY_CONSUMED,
                    CustodyTransfer.STATUS_EXPIRED_REVIEW,
                    CustodyTransfer.STATUS_RECONCILED,
                ],
            ).aggregate(total=Sum("returned_qty")).get("total")
            or Decimal("0")
        )
        return (Decimal(str(accepted_total)) - Decimal(str(returned_total))).quantize(Decimal("0.001"))

    @staticmethod
    def _guard_farm_scope(*, farm: Farm, supervisor: Supervisor, item: Item, source_location: Location) -> None:
        if supervisor.farm_id != farm.id:
            raise ValidationError({"supervisor_id": "المشرف لا يتبع نفس المزرعة."})
        if source_location.farm_id != farm.id:
            raise ValidationError({"from_location_id": "موقع المصدر لا يتبع نفس المزرعة."})
        if ItemInventory.objects.filter(farm=farm, item=item, location=source_location).exists():
            return
        # We still allow issue if stock exists via movement history and balance lookup.
        if InventoryService.get_stock_level(farm=farm, item=item, location=source_location) <= Decimal("0"):
            raise ValidationError({"qty": "الرصيد غير كافٍ في موقع المصدر."})

    @staticmethod
    @transaction.atomic
    def issue_transfer(
        *,
        farm: Farm,
        supervisor: Supervisor,
        item: Item,
        source_location: Location,
        qty,
        actor,
        batch_number: str = "",
        note: str = "",
        allow_top_up: bool = False,
        idempotency_key: str = "",
    ) -> CustodyTransfer:
        requested_qty = CustodyTransferService._as_decimal(qty, field_name="qty")
        CustodyTransferService._guard_farm_scope(
            farm=farm,
            supervisor=supervisor,
            item=item,
            source_location=source_location,
        )

        existing_balance = CustodyTransferService.get_item_custody_balance(
            farm=farm,
            supervisor=supervisor,
            item=item,
        )
        issue_qty = requested_qty
        if existing_balance > Decimal("0.000"):
            if not allow_top_up:
                raise ValidationError(
                    {
                        "qty": (
                            "لا يمكن إصدار عهدة جديدة لنفس الصنف قبل تصفية العهدة السابقة "
                            f"(الرصيد القائم: {existing_balance})."
                        )
                    }
                )
            issue_qty = (requested_qty - existing_balance).quantize(Decimal("0.001"))
            if issue_qty <= Decimal("0.000"):
                raise ValidationError(
                    {"qty": "الرصيد الحالي في عهدة المشرف يغطي الطلب المطلوب بالكامل."}
                )

        if idempotency_key:
            existing = CustodyTransfer.objects.filter(
                farm=farm,
                supervisor=supervisor,
                item=item,
                idempotency_key=idempotency_key,
                deleted_at__isnull=True,
            ).order_by("-id").first()
            if existing:
                return existing

        transit_location = CustodyTransferService._get_or_create_in_transit_location(farm=farm)
        custody_location = CustodyTransferService._get_or_create_custody_location(
            farm=farm,
            supervisor=supervisor,
        )
        now = timezone.now()
        transfer = CustodyTransfer.objects.create(
            farm=farm,
            supervisor=supervisor,
            item=item,
            source_location=source_location,
            in_transit_location=transit_location,
            custody_location=custody_location,
            batch_number=batch_number or "",
            status=CustodyTransfer.STATUS_ISSUED_PENDING_ACCEPTANCE,
            issued_qty=issue_qty,
            accepted_qty=Decimal("0.000"),
            returned_qty=Decimal("0.000"),
            note=note or "",
            idempotency_key=idempotency_key or "",
            issued_at=now,
            expires_at=now + timedelta(days=7),
            issued_by=actor,
        )
        InventoryService.transfer_stock(
            farm=farm,
            item=item,
            from_loc=source_location,
            to_loc=transit_location,
            qty=issue_qty,
            user=actor,
            batch_number=batch_number or None,
        )
        CustodyTransferService._append_audit(
            actor=actor,
            farm=farm,
            action="custody_issue",
            transfer=transfer,
            payload={
                "item_id": item.id,
                "supervisor_id": supervisor.id,
                "source_location_id": source_location.id,
                "transit_location_id": transit_location.id,
                "qty": str(issue_qty),
                "existing_balance": str(existing_balance),
                "allow_top_up": bool(allow_top_up),
            },
            reason=note or "custody_issue",
        )
        return transfer

    @staticmethod
    @transaction.atomic
    def accept_transfer(*, transfer: CustodyTransfer, actor, note: str = "") -> CustodyTransfer:
        transfer = CustodyTransfer.objects.select_for_update().get(pk=transfer.pk)
        if transfer.status in (
            CustodyTransfer.STATUS_ACCEPTED,
            CustodyTransfer.STATUS_PARTIALLY_CONSUMED,
            CustodyTransfer.STATUS_RETURNED,
            CustodyTransfer.STATUS_RECONCILED,
        ):
            return transfer
        if transfer.status != CustodyTransfer.STATUS_ISSUED_PENDING_ACCEPTANCE:
            raise ValidationError({"status": "لا يمكن قبول عهدة ليست في حالة انتظار القبول."})

        InventoryService.transfer_stock(
            farm=transfer.farm,
            item=transfer.item,
            from_loc=transfer.in_transit_location,
            to_loc=transfer.custody_location,
            qty=transfer.issued_qty,
            user=actor,
            batch_number=transfer.batch_number or None,
        )
        transfer.status = CustodyTransfer.STATUS_ACCEPTED
        transfer.accepted_qty = transfer.issued_qty
        transfer.accepted_at = timezone.now()
        transfer.accepted_by = actor
        if note:
            transfer.note = note
        transfer.save(
            update_fields=[
                "status",
                "accepted_qty",
                "accepted_at",
                "accepted_by",
                "note",
                "updated_at",
            ]
        )
        CustodyTransferService._append_audit(
            actor=actor,
            farm=transfer.farm,
            action="custody_accept",
            transfer=transfer,
            payload={"qty": str(transfer.accepted_qty), "custody_location_id": transfer.custody_location_id},
            reason=note or "custody_accept",
        )
        return transfer

    @staticmethod
    @transaction.atomic
    def reject_transfer(*, transfer: CustodyTransfer, actor, note: str = "") -> CustodyTransfer:
        transfer = CustodyTransfer.objects.select_for_update().get(pk=transfer.pk)
        if transfer.status == CustodyTransfer.STATUS_REJECTED:
            return transfer
        if transfer.status != CustodyTransfer.STATUS_ISSUED_PENDING_ACCEPTANCE:
            raise ValidationError({"status": "لا يمكن رفض عهدة بعد قبولها أو تسويتها."})

        InventoryService.transfer_stock(
            farm=transfer.farm,
            item=transfer.item,
            from_loc=transfer.in_transit_location,
            to_loc=transfer.source_location,
            qty=transfer.issued_qty,
            user=actor,
            batch_number=transfer.batch_number or None,
        )
        transfer.status = CustodyTransfer.STATUS_REJECTED
        transfer.rejected_at = timezone.now()
        transfer.rejected_by = actor
        if note:
            transfer.note = note
        transfer.save(update_fields=["status", "rejected_at", "rejected_by", "note", "updated_at"])
        CustodyTransferService._append_audit(
            actor=actor,
            farm=transfer.farm,
            action="custody_reject",
            transfer=transfer,
            payload={"qty": str(transfer.issued_qty), "source_location_id": transfer.source_location_id},
            reason=note or "custody_reject",
        )
        return transfer

    @staticmethod
    @transaction.atomic
    def return_transfer(*, transfer: CustodyTransfer, actor, qty=None, note: str = "") -> CustodyTransfer:
        transfer = CustodyTransfer.objects.select_for_update().get(pk=transfer.pk)
        if transfer.status not in (
            CustodyTransfer.STATUS_ACCEPTED,
            CustodyTransfer.STATUS_PARTIALLY_CONSUMED,
            CustodyTransfer.STATUS_EXPIRED_REVIEW,
        ):
            raise ValidationError({"status": "لا يمكن إرجاع عهدة غير مقبولة."})

        available_qty = CustodyTransferService.get_item_custody_balance(
            farm=transfer.farm,
            supervisor=transfer.supervisor,
            item=transfer.item,
        )
        return_qty = (
            CustodyTransferService._as_decimal(qty, field_name="qty")
            if qty not in (None, "", 0)
            else available_qty
        )
        if return_qty > available_qty:
            raise ValidationError({"qty": "كمية الإرجاع تتجاوز الرصيد المتاح في عهدة المشرف."})

        InventoryService.transfer_stock(
            farm=transfer.farm,
            item=transfer.item,
            from_loc=transfer.custody_location,
            to_loc=transfer.source_location,
            qty=return_qty,
            user=actor,
            batch_number=transfer.batch_number or None,
        )
        transfer.returned_qty = (transfer.returned_qty + return_qty).quantize(Decimal("0.001"))
        transfer.reconciled_at = timezone.now()
        transfer.reconciled_by = actor
        if note:
            transfer.note = note
        outstanding = (transfer.accepted_qty - transfer.returned_qty).quantize(Decimal("0.001"))
        transfer.status = (
            CustodyTransfer.STATUS_RECONCILED
            if outstanding <= Decimal("0.000")
            else CustodyTransfer.STATUS_PARTIALLY_CONSUMED
        )
        transfer.save(
            update_fields=["returned_qty", "reconciled_at", "reconciled_by", "status", "note", "updated_at"]
        )
        CustodyTransferService._append_audit(
            actor=actor,
            farm=transfer.farm,
            action="custody_return",
            transfer=transfer,
            payload={"qty": str(return_qty), "remaining_qty": str(outstanding)},
            reason=note or "custody_return",
        )
        return transfer

    @staticmethod
    @transaction.atomic
    def refresh_status_for_item(*, farm: Farm, supervisor: Supervisor, item: Item) -> None:
        current_balance = CustodyTransferService.get_item_custody_balance(
            farm=farm,
            supervisor=supervisor,
            item=item,
        )
        open_transfers: Iterable[CustodyTransfer] = CustodyTransfer.objects.select_for_update().filter(
            farm=farm,
            supervisor=supervisor,
            item=item,
            deleted_at__isnull=True,
            status__in=[
                CustodyTransfer.STATUS_ACCEPTED,
                CustodyTransfer.STATUS_PARTIALLY_CONSUMED,
                CustodyTransfer.STATUS_EXPIRED_REVIEW,
            ],
        )
        target_status = (
            CustodyTransfer.STATUS_PARTIALLY_CONSUMED
            if current_balance > Decimal("0.000")
            else CustodyTransfer.STATUS_RECONCILED
        )
        for transfer in open_transfers:
            if transfer.status != target_status:
                transfer.status = target_status
                transfer.save(update_fields=["status", "updated_at"])

    @staticmethod
    def get_consumption_location_for_activity(*, activity, item: Item, required_qty: Decimal) -> Optional[Location]:
        log = getattr(activity, "log", None)
        supervisor = getattr(log, "supervisor", None)
        farm = getattr(log, "farm", None)
        
        # [AGRI-GUARDIAN §17] Consumption Site Resolution
        if supervisor and farm:
            custody_location = CustodyTransferService.get_supervisor_custody_location(
                farm=farm,
                supervisor=supervisor,
            )
            on_hand = InventoryService.get_stock_level(farm=farm, item=item, location=custody_location)
            if on_hand < required_qty:
                raise ValidationError(
                    {
                        "shortages": (
                            f"رصيد عهدة المشرف غير كافٍ للصنف {item.name}. "
                            f"المتاح: {on_hand}, المطلوب: {required_qty}."
                        )
                    }
                )
            return custody_location

        # [SIMPLE MODE / NO SUPERVISOR] Fallback Strategy
        # First check the activity's physical location.
        first_location_entry = activity.activity_locations.first()
        activity_location = first_location_entry.location if first_location_entry else None
        
        if activity_location and farm:
            on_hand_at_loc = InventoryService.get_stock_level(farm=farm, item=item, location=activity_location)
            if on_hand_at_loc >= required_qty:
                return activity_location
        
        # Final Fallback: Farm General Store (location=None)
        return None

    @staticmethod
    def custody_balance_payload(*, farm: Farm, supervisor: Supervisor) -> dict:
        custody_location = CustodyTransferService.get_supervisor_custody_location(
            farm=farm,
            supervisor=supervisor,
        )
        balances = (
            ItemInventory.objects.filter(
                farm=farm,
                location=custody_location,
                deleted_at__isnull=True,
                qty__gt=Decimal("0.000"),
            )
            .select_related("item")
            .order_by("item__name")
        )
        active_transfers = CustodyTransfer.objects.filter(
            farm=farm,
            supervisor=supervisor,
            deleted_at__isnull=True,
        ).select_related("item", "source_location")
        return {
            "supervisor_id": supervisor.id,
            "farm_id": farm.id,
            "custody_location_id": custody_location.id,
            "balances": [
                {
                    "item_id": entry.item_id,
                    "item_name": entry.item.name,
                    "qty": str(entry.qty),
                    "uom": entry.item.uom,
                }
                for entry in balances
            ],
            "transfers": [
                {
                    "id": transfer.id,
                    "item_id": transfer.item_id,
                    "item_name": transfer.item.name,
                    "status": transfer.status,
                    "issued_qty": str(transfer.issued_qty),
                    "accepted_qty": str(transfer.accepted_qty),
                    "returned_qty": str(transfer.returned_qty),
                    "source_location_id": transfer.source_location_id,
                    "source_location_name": transfer.source_location.name,
                }
                for transfer in active_transfers
            ],
        }
