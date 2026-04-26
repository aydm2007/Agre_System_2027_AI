from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.utils import timezone

from smart_agri.core.api.permissions import user_has_farm_role
from smart_agri.core.models.settings import FarmSettings
from smart_agri.finance.models_supplier_settlement import (
    SupplierSettlement,
    SupplierSettlementPayment,
)
from smart_agri.finance.models_treasury import CashBox, TreasuryTransaction
from smart_agri.inventory.models import PurchaseOrder
from smart_agri.finance.services.farm_finance_authority_service import FarmFinanceAuthorityService
from smart_agri.core.decorators import enforce_strict_mode


class SupplierSettlementService:
    FINANCE_ROLES = {
        "مدير المزرعة",
        "المدير المالي للمزرعة",
        "رئيس الحسابات",
        "محاسب القطاع",
        "مراجع القطاع",
        "رئيس حسابات القطاع",
        "المدير المالي لقطاع المزارع",
        "مدير القطاع",
        "مدير النظام",
    }

    @staticmethod
    def _require_finance_authority(user, farm, strict_only=False):
        settings_obj = SupplierSettlementService._farm_settings(farm)
        if getattr(settings_obj, 'mode', FarmSettings.MODE_SIMPLE) != FarmSettings.MODE_STRICT:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("🔴 [FORENSIC BLOCK] Service execution blocked: STRICT mode required.")
            
        if getattr(user, "is_superuser", False):
            return
        if strict_only and user.has_perm("finance.can_approve_finance_request"):
            return
        if user.has_perm("finance.can_post_treasury"):
            return
        if user_has_farm_role(user, farm.id, SupplierSettlementService.FINANCE_ROLES):
            FarmFinanceAuthorityService.require_strict_cycle_authority(user=user, farm=farm, action_label='إجراء تسوية مورد')
            return
        raise ValidationError("Supplier settlement action requires governed finance authority.")

    @staticmethod
    def _sync_status(settlement: SupplierSettlement) -> SupplierSettlement:
        paid_total = (
            settlement.payments.filter(deleted_at__isnull=True)
            .values_list("amount", flat=True)
        )
        settlement.paid_amount = sum(paid_total, Decimal("0.0000"))
        if settlement.paid_amount == settlement.payable_amount:
            settlement.status = SupplierSettlement.STATUS_PAID
        elif settlement.paid_amount > Decimal("0.0000"):
            settlement.status = SupplierSettlement.STATUS_PARTIALLY_PAID
        elif settlement.status == SupplierSettlement.STATUS_PARTIALLY_PAID:
            settlement.status = SupplierSettlement.STATUS_APPROVED
        settlement.full_clean()
        settlement.save(update_fields=["paid_amount", "status", "updated_at"])
        return settlement

    @staticmethod
    def _farm_settings(farm):
        settings_obj = getattr(farm, "settings", None)
        if settings_obj is not None:
            return settings_obj
        settings_obj, _ = FarmSettings.objects.get_or_create(farm=farm)
        return settings_obj

    @staticmethod
    @transaction.atomic
    def create_draft(
        *,
        user,
        purchase_order_id,
        invoice_reference="",
        due_date=None,
        payment_method=SupplierSettlement.PAYMENT_METHOD_CASH_BOX,
        cost_center=None,
        crop_plan=None,
    ) -> SupplierSettlement:
        po = (
            PurchaseOrder.objects.select_for_update()
            .select_related("farm")
            .get(pk=purchase_order_id, deleted_at__isnull=True)
        )
        SupplierSettlementService._require_finance_authority(user, po.farm)
        if po.status not in {PurchaseOrder.Status.APPROVED, PurchaseOrder.Status.RECEIVED}:
            raise ValidationError("Purchase order must be approved before creating supplier settlement.")
        if hasattr(po, "supplier_settlement"):
            raise ValidationError("This purchase order already has a supplier settlement.")

        settlement = SupplierSettlement.objects.create(
            farm=po.farm,
            purchase_order=po,
            invoice_reference=(invoice_reference or f"PO-{po.id}").strip(),
            due_date=due_date or po.expected_delivery_date or po.order_date,
            payment_method=payment_method,
            payable_amount=po.total_amount,
            cost_center=cost_center,
            crop_plan=crop_plan,
            created_by=user,
        )
        return settlement

    @staticmethod
    @transaction.atomic
    def submit_review(settlement_id, user) -> SupplierSettlement:
        settlement = SupplierSettlement.objects.select_for_update().get(pk=settlement_id)
        SupplierSettlementService._require_finance_authority(user, settlement.farm)
        if settlement.status not in {SupplierSettlement.STATUS_DRAFT, SupplierSettlement.STATUS_REOPENED}:
            raise ValidationError("Only draft or reopened settlements can move to review.")
        
        # [AGRI-GUARDIAN] Single-role collapse prevention
        if settlement.created_by_id == user.id:
            raise ValidationError("⚠️ [GOVERNANCE BLOCK] الفصل في المهام: لا يمكن لمنشئ التسوية أن يكون هو المراجع.")

        settlement.status = SupplierSettlement.STATUS_UNDER_REVIEW
        settlement.reviewed_by = user
        settlement.reviewed_at = timezone.now()
        settlement.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
        return settlement

    @staticmethod
    @transaction.atomic
    def approve(settlement_id, user) -> SupplierSettlement:
        settlement = SupplierSettlement.objects.select_for_update().select_related("farm").get(pk=settlement_id)
        enforce_strict_mode(settlement.farm)
        
        from smart_agri.core.services.farm_tiering_policy_service import FarmTieringPolicyService
        from smart_agri.accounts.models import FarmMembership
        snapshot = FarmTieringPolicyService.snapshot(getattr(settlement.farm, 'tier', 'SMALL'))
        if snapshot.get("requires_farm_finance_manager"):
            has_ffm = FarmMembership.objects.filter(
                farm_id=settlement.farm_id,
                role__in=FarmFinanceAuthorityService.FARM_FINANCE_MANAGER_ROLES
            ).exists()
            if not has_ffm:
                raise ValidationError("اعتماد تسوية المورد النهائي يتطلب وجود 'المدير المالي للمزرعة' المعين بناءً على حجم المزرعة.")
                
        approval_profile = getattr(
            SupplierSettlementService._farm_settings(settlement.farm),
            "approval_profile",
            FarmSettings.APPROVAL_PROFILE_TIERED,
        )
        SupplierSettlementService._require_finance_authority(
            user,
            settlement.farm,
            strict_only=approval_profile == FarmSettings.APPROVAL_PROFILE_STRICT_FINANCE,
        )
        FarmFinanceAuthorityService.require_profiled_posting_authority(
            user=user,
            farm=settlement.farm,
            action_label='اعتماد نهائي لتسوية المورد',
        )
        if settlement.status != SupplierSettlement.STATUS_UNDER_REVIEW:
            raise ValidationError("Only settlements under review can be approved.")

        # [AGRI-GUARDIAN] Single-role collapse prevention
        if settlement.created_by_id == user.id:
            raise ValidationError("⚠️ [GOVERNANCE BLOCK] الفصل في المهام: لا يمكن لمنشئ التسوية أن يكون المعتمد النهائي.")
        if settlement.reviewed_by_id == user.id:
            raise ValidationError("⚠️ [GOVERNANCE BLOCK] الفصل في المهام: لا يمكن لمراجع التسوية أن يكون المعتمد النهائي.")



        # [AGRI-GUARDIAN Axis 12] Enforce Attachment Governance for STRICT mode
        if getattr(SupplierSettlementService._farm_settings(settlement.farm), 'mode', FarmSettings.MODE_SIMPLE) == FarmSettings.MODE_STRICT:
            if getattr(SupplierSettlementService._farm_settings(settlement.farm), 'mandatory_attachment_for_cash', True):
                from smart_agri.core.models.log import Attachment
                has_attachment = Attachment.objects.filter(
                    farm_id=settlement.farm_id,
                    related_document_type="supplier_settlement",
                    document_scope=str(settlement.id)
                ).exclude(malware_scan_status=Attachment.MALWARE_SCAN_QUARANTINED).exists()
                if not has_attachment:
                    raise ValidationError("🔴 [GOVERNANCE BLOCK] يتطلب الاعتماد النهائي في المود الصارم وجود مرفق سليم (غير محجور) يدعم الدفعة/التسوية.")
        settlement.status = SupplierSettlement.STATUS_APPROVED
        settlement.approved_by = user
        settlement.approved_at = timezone.now()
        settlement.rejected_reason = ""
        settlement.save(
            update_fields=["status", "approved_by", "approved_at", "rejected_reason", "updated_at"]
        )
        return settlement

    @staticmethod
    @transaction.atomic
    def reject(settlement_id, user, reason="") -> SupplierSettlement:
        settlement = SupplierSettlement.objects.select_for_update().get(pk=settlement_id)
        SupplierSettlementService._require_finance_authority(user, settlement.farm)
        if settlement.status not in {SupplierSettlement.STATUS_UNDER_REVIEW, SupplierSettlement.STATUS_APPROVED}:
            raise ValidationError("Only settlements under review or approved can be rejected.")
        settlement.status = SupplierSettlement.STATUS_REJECTED
        settlement.rejected_reason = (reason or "").strip()
        settlement.save(update_fields=["status", "rejected_reason", "updated_at"])
        return settlement

    @staticmethod
    @transaction.atomic
    def reopen(settlement_id, user) -> SupplierSettlement:
        settlement = SupplierSettlement.objects.select_for_update().get(pk=settlement_id)
        SupplierSettlementService._require_finance_authority(user, settlement.farm)
        if settlement.status != SupplierSettlement.STATUS_REJECTED:
            raise ValidationError("Only rejected settlements can be reopened.")
        settlement.status = SupplierSettlement.STATUS_REOPENED
        settlement.save(update_fields=["status", "updated_at"])
        return settlement

    @staticmethod
    @transaction.atomic
    def record_payment(
        *,
        settlement_id,
        cash_box_id,
        amount,
        user,
        idempotency_key,
        note="",
        reference="",
    ) -> SupplierSettlement:
        settlement = (
            SupplierSettlement.objects.select_for_update()
            .select_related("farm", "purchase_order")
            .get(pk=settlement_id)
        )
        enforce_strict_mode(settlement.farm)
        if settlement.status not in {
            SupplierSettlement.STATUS_APPROVED,
            SupplierSettlement.STATUS_PARTIALLY_PAID,
        }:
            raise ValidationError("Settlement must be approved before recording payments.")
        if settlement.purchase_order.status not in {PurchaseOrder.Status.APPROVED, PurchaseOrder.Status.RECEIVED}:
            raise ValidationError("Payment without a valid approved payable source is forbidden.")

        SupplierSettlementService._require_finance_authority(user, settlement.farm)
        FarmFinanceAuthorityService.require_profiled_posting_authority(
            user=user,
            farm=settlement.farm,
            action_label='ترحيل دفعة مورد',
        )

        settings = SupplierSettlementService._farm_settings(settlement.farm)
        if settings.treasury_visibility == FarmSettings.TREASURY_VISIBILITY_HIDDEN and not getattr(user, "is_superuser", False):
            raise ValidationError("Treasury visibility policy blocks payment posting for this farm.")

        amount_decimal = Decimal(str(amount or "0")).quantize(Decimal("0.0001"))
        if amount_decimal <= Decimal("0.0000"):
            raise ValidationError("Payment amount must be greater than zero.")
        if amount_decimal > settlement.remaining_balance:
            raise ValidationError("Payment amount cannot exceed the remaining supplier balance.")

        try:
            cash_box = CashBox.objects.select_for_update().get(pk=cash_box_id, farm_id=settlement.farm_id)
        except ObjectDoesNotExist as exc:
            raise ValidationError("Cash box must belong to the same farm.") from exc

        payment_count = settlement.payments.filter(deleted_at__isnull=True).count() + 1
        treasury_reference = (reference or f"SUPSET-{settlement.id}-{payment_count}").strip()
        treasury_tx = TreasuryTransaction(
            farm=settlement.farm,
            cash_box=cash_box,
            transaction_type=TreasuryTransaction.PAYMENT,
            amount=amount_decimal,
            exchange_rate=Decimal("1.0000"),
            reference=treasury_reference[:120],
            note=(note or f"Supplier settlement for {settlement.vendor_name} / PO-{settlement.purchase_order_id}")[:500],
            idempotency_key=idempotency_key,
            created_by=user,
            cost_center=settlement.cost_center,
            analytical_tags={
                "supplier_settlement_id": settlement.id,
                "purchase_order_id": settlement.purchase_order_id,
                "vendor_name": settlement.vendor_name,
                "payment_method": settlement.payment_method,
            },
        )
        treasury_tx.save()

        SupplierSettlementPayment.objects.create(
            settlement=settlement,
            treasury_transaction=treasury_tx,
            amount=amount_decimal,
            note=(note or "").strip(),
            created_by=user,
        )

        settlement.latest_treasury_transaction = treasury_tx
        settlement.save(update_fields=["latest_treasury_transaction", "updated_at"])
        return SupplierSettlementService._sync_status(settlement)

    @staticmethod
    @transaction.atomic
    def record_batch_payment(
        *,
        settlements_data: list,  # [{"settlement_id": 1, "amount": Decimal('100.00')}, ...]
        cash_box_id: int,
        user,
        idempotency_key: str,
        note: str = "",
        reference: str = "",
    ) -> list[SupplierSettlement]:
        """
        Record a single treasury transaction (cash outflow) that settles multiple supplier settlements.
        """
        if not settlements_data:
            raise ValidationError("No settlements provided for batch payment.")

        total_amount = sum((s["amount"] for s in settlements_data), Decimal("0.0000"))
        if total_amount <= Decimal("0.0000"):
            raise ValidationError("Total batch payment amount must be greater than zero.")

        # Ensure all settlements exist, are from the same farm, and are approved
        settlement_ids = [s["settlement_id"] for s in settlements_data]
        settlements = SupplierSettlement.objects.select_for_update().select_related("farm", "purchase_order").filter(pk__in=settlement_ids)
        
        if len(settlements) != len(settlement_ids):
            raise ValidationError("One or more supplier settlements were not found.")

        farm_ids = {s.farm_id for s in settlements}
        if len(farm_ids) > 1:
            raise ValidationError("Batch payments cannot span multiple farms.")
            
        farm_id = farm_ids.pop()
        farm = settlements[0].farm
        
        SupplierSettlementService._require_finance_authority(user, farm)
        enforce_strict_mode(farm)

        settings_obj = SupplierSettlementService._farm_settings(farm)
        if settings_obj.treasury_visibility == FarmSettings.TREASURY_VISIBILITY_HIDDEN and not getattr(user, "is_superuser", False):
            raise ValidationError("Treasury visibility policy blocks payment posting for this farm.")

        try:
            cash_box = CashBox.objects.select_for_update().get(pk=cash_box_id, farm_id=farm_id)
        except ObjectDoesNotExist as exc:
            raise ValidationError("Cash box must belong to the same farm.") from exc

        # Create the single collective treasury transaction
        treasury_reference = (reference or f"BATCH-SUPSET-{idempotency_key[-6:]}").strip()
        treasury_tx = TreasuryTransaction(
            farm=farm,
            cash_box=cash_box,
            transaction_type=TreasuryTransaction.PAYMENT,
            amount=total_amount.quantize(Decimal("0.0001")),
            exchange_rate=Decimal("1.0000"),
            reference=treasury_reference[:120],
            note=(note or "Batch Supplier Payment")[:500],
            idempotency_key=idempotency_key,
            created_by=user,
            analytical_tags={"batch_payment": True, "settlement_count": len(settlement_ids)},
        )
        treasury_tx.save()

        updated_settlements = []
        # Process individual payments
        for data in settlements_data:
            sid = data["settlement_id"]
            amount_decimal = Decimal(str(data["amount"])).quantize(Decimal("0.0001"))
            
            settlement = next(s for s in settlements if s.id == sid)
            
            if settlement.status not in {SupplierSettlement.STATUS_APPROVED, SupplierSettlement.STATUS_PARTIALLY_PAID}:
                raise ValidationError(f"Settlement {sid} must be approved before recording payments.")
            if settlement.purchase_order.status not in {PurchaseOrder.Status.APPROVED, PurchaseOrder.Status.RECEIVED}:
                raise ValidationError(f"Settlement {sid} has an unapproved payable source.")
            
            if amount_decimal > settlement.remaining_balance:
                raise ValidationError(f"Payment amount cannot exceed the remaining balance for settlement {sid}.")

            SupplierSettlementPayment.objects.create(
                settlement=settlement,
                treasury_transaction=treasury_tx,
                amount=amount_decimal,
                note=(note or f"Batch Payment Part").strip(),
                created_by=user,
            )

            settlement.latest_treasury_transaction = treasury_tx
            settlement.save(update_fields=["latest_treasury_transaction", "updated_at"])
            updated_settlements.append(SupplierSettlementService._sync_status(settlement))

        return updated_settlements
