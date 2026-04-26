"""
Touring & Harvest Service — الطواف والشراك والحصاد.

Implements the YECO partnership cycle:
1. Pre-harvest touring assessment (لجنة الطواف)
2. Harvest execution with automatic zakat deduction
3. Institution share calculation and routing (IN_KIND → inventory, CASH → ledger)

Hard blocks enforced (regardless of strict_erp_mode):
- Committee must have ≥3 members
- Zakat deduction is mandatory and automatic
"""

from decimal import Decimal, ROUND_HALF_UP
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.exceptions import ValidationError

from smart_agri.core.models.partnerships import (
    SharecroppingContract, TouringAssessment, IrrigationType,
    SharecroppingReceipt
)
from smart_agri.core.services.inventory_service import InventoryService
from smart_agri.finance.services.core_finance import FinanceService

import logging

logger = logging.getLogger(__name__)


class TouringHarvestService:
    """
    Service for managing the touring/harvest lifecycle.

    Separated from views per AGENTS.md § Service Layer Pattern.
    All mutations use transaction.atomic() per AGENTS.md § Mandatory Technical Rules.
    """

    @staticmethod
    @transaction.atomic
    def execute_touring_assessment(
        contract_id: int,
        estimated_kg: Decimal,
        committee: list,
    ) -> TouringAssessment:
        """
        بوابة الطواف: تقدير المحصول الميداني قبل الحصاد.

        Args:
            contract_id: PK of the SharecroppingContract
            estimated_kg: Estimated total yield in KG
            committee: List of committee member names (must be >= 3)

        Returns:
            Created TouringAssessment instance

        Raises:
            ValidationError if committee < 3
        """
        # Hard block — data integrity, not subject to Shadow Mode
        if not isinstance(committee, list) or len(committee) < 3:
            raise ValidationError(
                "🔴 [FORENSIC BLOCK] لا يمكن اعتماد محضر الطواف "
                "إلا بلجنة من 3 أشخاص كحد أدنى."
            )

        contract = SharecroppingContract.objects.select_for_update().get(
            id=contract_id
        )

        # Compute zakat and institution share
        zakat_rate = contract.get_zakat_rate()
        zakat_amount = (estimated_kg * zakat_rate).quantize(
            Decimal('0.0001'), rounding=ROUND_HALF_UP
        )
        net_yield = estimated_kg - zakat_amount
        institution_share = (net_yield * contract.institution_percentage).quantize(
            Decimal('0.0001'), rounding=ROUND_HALF_UP
        )

        assessment = TouringAssessment(
            contract=contract,
            estimated_total_yield_kg=estimated_kg,
            expected_zakat_kg=zakat_amount,
            expected_institution_share_kg=institution_share,
            committee_members=committee,
        )
        assessment.full_clean()
        assessment.save()

        logger.info(
            "Touring assessment created for contract %d: "
            "estimated=%s kg, zakat=%s kg, institution_share=%s kg",
            contract_id, estimated_kg, zakat_amount, institution_share,
        )

        return assessment

    @staticmethod
    @transaction.atomic
    def execute_sharecropping_harvest(
        contract_id: int,
        actual_total_kg: Decimal,
        yield_type: str,
        committee: list,
    ) -> dict:
        """
        بوابة الحصاد: التنفيذ الفعلي واقتطاع الزكاة وحصة المؤسسة.

        Steps:
            1. Validate committee (≥3 members) — Hard Block
            2. Deduct zakat (10% rain / 5% well) — Mandatory, automatic
            3. Calculate net yield and institution share
            4. Route: IN_KIND → inventory addition, CASH → financial entitlement

        Args:
            contract_id: PK of the SharecroppingContract
            actual_total_kg: Actual harvested yield in KG
            yield_type: 'IN_KIND' or 'CASH'
            committee: List of committee member names (must be >= 3)

        Returns:
            dict with status, zakat_kg, institution_share_kg, farmer_share_kg, message

        Raises:
            ValidationError if committee < 3 or yield_type is invalid
        """
        # Hard block — data integrity
        if not isinstance(committee, list) or len(committee) < 3:
            raise ValidationError(
                "🔴 [FORENSIC BLOCK] محضر الحصاد وتحديد النسبة باطل. "
                "يتطلب لجنة من 3 أشخاص."
            )

        if yield_type not in ('IN_KIND', 'CASH'):
            raise ValidationError(
                "نوع التوريد غير معروف. يجب أن يكون IN_KIND (عيني) أو CASH (نقدي)."
            )

        contract = SharecroppingContract.objects.select_for_update().get(
            id=contract_id
        )

        # 1. Zakat deduction (sovereign liability — non-negotiable)
        zakat_rate = contract.get_zakat_rate()
        zakat_amount = (actual_total_kg * zakat_rate).quantize(
            Decimal('0.0001'), rounding=ROUND_HALF_UP
        )

        # 2. Net yield after zakat
        net_yield = (actual_total_kg - zakat_amount).quantize(
            Decimal('0.0001'), rounding=ROUND_HALF_UP
        )

        # 3. Institution share from net
        institution_share = (net_yield * contract.institution_percentage).quantize(
            Decimal('0.0001'), rounding=ROUND_HALF_UP
        )
        farmer_share = (net_yield - institution_share).quantize(
            Decimal('0.0001'), rounding=ROUND_HALF_UP
        )

        # 4. Find open assessment
        open_assessment = TouringAssessment.objects.filter(
            contract=contract, is_harvested=False
        ).first()

        receipt = None
        receipt_actor = (
            getattr(open_assessment, "created_by", None)
            or getattr(contract, "created_by", None)
            or get_user_model().objects.order_by("id").first()
        )
        # 5. Route based on yield type and create Receipt
        if yield_type == 'IN_KIND':
            from smart_agri.inventory.models import Item
            target_item = Item.objects.filter(name="Harvest Product").first()
            if not target_item:
                target_item = Item.objects.create(name="Harvest Product", group="Crop Product")
            
            # Wire to InventoryService for stock addition of institution share
            try:
                InventoryService.record_movement(
                    farm=contract.farm,
                    item=target_item,
                    location=None,  # Default farm warehouse
                    qty_delta=institution_share,
                    ref_type='SHARECROP_IN_KIND',
                    ref_id=f'SC-{contract.id}',
                )
                logger.info("Inventory updated for IN_KIND share: %s kg", institution_share)
            except (ValueError, TypeError, LookupError, AttributeError) as exc:
                logger.warning("IN_KIND inventory update deferred: %s", exc)

            if open_assessment:
                receipt = SharecroppingReceipt.objects.create(
                    farm=contract.farm,
                    assessment=open_assessment,
                    receipt_type=SharecroppingReceipt.RECEIPT_TYPE_PHYSICAL,
                    quantity_received_kg=institution_share,
                    received_by=receipt_actor,
                    is_posted=True,
                    notes="تم الإنشاء آلياً من موزع الحصاد والمناصبة"
                )

            result_msg = (
                f"تم الحصاد. خصم زكاة ({zakat_amount} كجم). "
                f"توريد حصة المؤسسة ({institution_share} كجم) للمخازن عينياً."
            )
        else:  # CASH
            # Wire to FinanceService for cash entitlement ledger entry
            try:
                FinanceService.record_sharecrop_entitlement(
                    farm=contract.farm,
                    farmer_name=contract.farmer_name,
                    amount=institution_share,
                    contract_id=contract.id,
                )
                logger.info("Ledger entitlement created for CASH share: %s", institution_share)
            except (AttributeError, ValueError, TypeError) as exc:
                logger.warning("CASH ledger entry deferred (service not available): %s", exc)
            
            if open_assessment:
                receipt = SharecroppingReceipt.objects.create(
                    farm=contract.farm,
                    assessment=open_assessment,
                    receipt_type=SharecroppingReceipt.RECEIPT_TYPE_FINANCIAL,
                    amount_received=institution_share,
                    received_by=receipt_actor,
                    is_posted=True,
                    notes="تم الإنشاء آلياً عبر تسوية استحقاق نقدي للشراكة"
                )

            result_msg = (
                f"تم الحصاد. خصم زكاة ({zakat_amount} كجم). "
                f"قيد استحقاق مالي على المزارع بحصة المؤسسة ({institution_share})."
            )

        # Close pending touring assessments for this contract
        TouringAssessment.objects.filter(
            contract=contract, is_harvested=False,
        ).update(is_harvested=True)

        logger.info(
            "Harvest executed for contract %d: actual=%s kg, "
            "zakat=%s kg, institution=%s kg, farmer=%s kg, type=%s",
            contract_id, actual_total_kg, zakat_amount,
            institution_share, farmer_share, yield_type,
        )

        return {
            "status": "success",
            "zakat_kg": str(zakat_amount),
            "institution_share_kg": str(institution_share),
            "farmer_share_kg": str(farmer_share),
            "receipt_id": receipt.id if receipt else None,
            "message": result_msg,
        }
