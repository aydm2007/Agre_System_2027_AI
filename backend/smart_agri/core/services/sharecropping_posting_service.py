"""
SharecroppingPostingService - Posts financial and physical sharecropping receipts.

Posts financial ledger entries when a SharecroppingReceipt is confirmed,
respecting FarmSettings.sharecropping_mode (FINANCIAL vs PHYSICAL).

AGENTS.md Compliance:
  - Axis 4: Fund Accounting
  - Axis 5: Decimal(19,4) - no float
  - Axis 6: farm_id isolation
  - Axis 7: AuditLog
  - Axis 15: Dual-mode sharecropping support
"""

import logging
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from smart_agri.finance.services.farm_finance_authority_service import FarmFinanceAuthorityService

logger = logging.getLogger(__name__)

FOUR_DP = Decimal("0.0001")
ZERO = Decimal("0.0000")


class SharecroppingPostingService:
    """Posts financial or physical entries for sharecropping receipts."""

    @staticmethod
    @transaction.atomic
    def post_receipt(*, receipt_id: int, user=None) -> dict:
        from smart_agri.core.models.partnerships import SharecroppingReceipt
        from smart_agri.core.models.settings import FarmSettings

        receipt = SharecroppingReceipt.objects.select_related(
            "assessment__contract__farm",
            "assessment__contract__crop",
            "destination_inventory__item",
            "destination_inventory__location",
        ).filter(
            pk=receipt_id,
            deleted_at__isnull=True,
        ).first()

        if not receipt:
            raise ValidationError({"receipt_id": "سند الاستلام غير موجود."})

        if receipt.is_posted:
            logger.info("Receipt %s already posted. Idempotent skip.", receipt_id)
            return {"status": "already_posted", "receipt_id": receipt_id}

        farm_id = receipt.farm_id
        contract = receipt.assessment.contract if receipt.assessment else None
        FarmFinanceAuthorityService.require_profiled_posting_authority(user=user, farm=receipt.assessment.contract.farm, action_label='ترحيل سند شراكة/طواف')

        try:
            farm_settings = FarmSettings.objects.get(farm_id=farm_id)
            sharecropping_mode = farm_settings.sharecropping_mode
        except FarmSettings.DoesNotExist:
            sharecropping_mode = FarmSettings.SHARECROPPING_MODE_FINANCIAL

        cost_center = None
        try:
            from smart_agri.finance.models import CostCenter

            cost_center = CostCenter.objects.filter(farm_id=farm_id, is_active=True).first()
        except (LookupError, ImportError):
            pass

        created_by = user if user and getattr(user, "is_authenticated", False) else None

        if sharecropping_mode == FarmSettings.SHARECROPPING_MODE_FINANCIAL:
            result = SharecroppingPostingService._post_financial(
                receipt=receipt,
                farm_id=farm_id,
                cost_center=cost_center,
                created_by=created_by,
            )
        else:
            result = SharecroppingPostingService._post_physical(
                receipt=receipt,
                farm_id=farm_id,
                cost_center=cost_center,
                created_by=created_by,
            )

        receipt.is_posted = True
        receipt.save(update_fields=["is_posted"])

        from smart_agri.core.models.log import AuditLog

        AuditLog.objects.create(
            action="SHARECROPPING_RECEIPT_POSTED",
            model="SharecroppingReceipt",
            object_id=str(receipt_id),
            actor=user,
            farm_id=farm_id,
            new_payload={
                "posting_mode": sharecropping_mode,
                "farm_id": farm_id,
                "farmer_name": contract.farmer_name if contract else "N/A",
                **result,
            },
        )

        logger.info(
            "Sharecropping receipt posted: receipt=%s, mode=%s, farm=%s",
            receipt_id,
            sharecropping_mode,
            farm_id,
        )

        return {
            "status": "posted",
            "receipt_id": receipt_id,
            "posting_mode": sharecropping_mode,
            **result,
        }

    @staticmethod
    def _post_financial(*, receipt, farm_id, cost_center, created_by) -> dict:
        from smart_agri.finance.models import FinancialLedger

        amount = receipt.amount_received
        if not amount or amount <= ZERO:
            raise ValidationError({"amount_received": "المبلغ المالي مطلوب في وضع الشراكة المالية."})
        amount = amount.quantize(FOUR_DP)

        description = f"حصة شراكة مالية - سند #{receipt.id} | المبلغ: {amount}"

        FinancialLedger.objects.create(
            farm_id=farm_id,
            account_code=FinancialLedger.ACCOUNT_CASH_ON_HAND,
            cost_center=cost_center,
            debit=amount,
            credit=ZERO,
            description=description,
            created_by=created_by,
        )
        FinancialLedger.objects.create(
            farm_id=farm_id,
            account_code=FinancialLedger.ACCOUNT_SALES_REVENUE,
            cost_center=cost_center,
            debit=ZERO,
            credit=amount,
            description=description,
            created_by=created_by,
        )

        return {"amount": str(amount)}

    @staticmethod
    def _post_physical(*, receipt, farm_id, cost_center, created_by) -> dict:
        from smart_agri.finance.models import FinancialLedger
        from smart_agri.inventory.models import StockMovement

        quantity = receipt.quantity_received_kg
        if not quantity or quantity <= ZERO:
            raise ValidationError({"quantity_received_kg": "الكمية العينية مطلوبة في وضع الشراكة العينية."})
        quantity = quantity.quantize(FOUR_DP)

        estimated_value = quantity
        destination_inventory = receipt.destination_inventory
        if destination_inventory and destination_inventory.item and destination_inventory.item.unit_price > ZERO:
            estimated_value = (quantity * destination_inventory.item.unit_price).quantize(FOUR_DP)

        description = (
            f"حصة شراكة عينية - سند #{receipt.id} | "
            f"الكمية: {quantity} كجم | القيمة التقديرية: {estimated_value}"
        )

        FinancialLedger.objects.create(
            farm_id=farm_id,
            account_code=FinancialLedger.ACCOUNT_INVENTORY_ASSET,
            cost_center=cost_center,
            debit=estimated_value,
            credit=ZERO,
            description=description,
            created_by=created_by,
        )
        FinancialLedger.objects.create(
            farm_id=farm_id,
            account_code=FinancialLedger.ACCOUNT_SALES_REVENUE,
            cost_center=cost_center,
            debit=ZERO,
            credit=estimated_value,
            description=description,
            created_by=created_by,
        )

        if destination_inventory:
            StockMovement.objects.create(
                farm_id=farm_id,
                item=destination_inventory.item,
                location=destination_inventory.location,
                qty_delta=quantity,
                ref_type="sharecropping_receipt",
                ref_id=str(receipt.id),
                note=f"Sharecropping physical receipt #{receipt.id}",
                batch_number=f"SHARECROP-{receipt.id}",
            )

        return {
            "quantity_kg": str(quantity),
            "estimated_value": str(estimated_value),
        }
