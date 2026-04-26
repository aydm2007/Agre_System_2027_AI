import logging
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.db.models import Sum, F
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger(__name__)

class SeasonalSettlementService:
    """
    [AGRI-GUARDIAN Phase 6] ERP Compliance: Seasonal WIP Settlement.
    Closes a seasonal Crop Plan by computing actual unit cost and flushing 
    residual Work In Progress (WIP) variances into Cost of Goods Sold (COGS).
    """

    @staticmethod
    @transaction.atomic
    def close_seasonal_crop_plan(farm, crop_plan, user=None, period_date=None, ref_id=""):
        """
        Closes the crop plan, computes actual per-kilo unit costs versus estimated,
        and posts the final WIP variance clearance entry.
        """
        from smart_agri.finance.models import FinancialLedger
        from smart_agri.finance.services.core_finance import FinanceService
        from smart_agri.core.models.inventory import HarvestLot
        from smart_agri.core.constants import CropPlanStatus

        period_date = period_date or timezone.now().date()
        FinanceService.check_fiscal_period(period_date, farm)

        if crop_plan.status == CropPlanStatus.COMPLETED:
            raise ValueError(f"Crop Plan {crop_plan.name} is already COMPLETED and financially closed.")

        if crop_plan.farm != farm:
            raise ValueError("Crop Plan does not belong to the requested farm.")

        plan_ctype = ContentType.objects.get_for_model(crop_plan.__class__)

        # 1. Gather Total WIP Account Balance (Debit - Credit)
        wip_qs = FinancialLedger.objects.filter(
            farm=farm,
            account_code=FinancialLedger.ACCOUNT_WIP,
            crop_plan=crop_plan
        ).aggregate(balance=Sum(F('debit') - F('credit')))
        
        residual_wip = wip_qs.get('balance') or Decimal("0.0000")

        # Gather Harvest Metrics for Analysis
        total_harvest_qty = HarvestLot.objects.filter(
            farm=farm,
            crop_plan=crop_plan,
            deleted_at__isnull=True
        ).aggregate(total=Sum('quantity'))['total'] or Decimal("0.000")

        original_debits_qs = FinancialLedger.objects.filter(
            farm=farm,
            account_code=FinancialLedger.ACCOUNT_WIP,
            crop_plan=crop_plan
        ).aggregate(total_debit=Sum('debit'))
        
        total_wip_incurred = original_debits_qs.get('total_debit') or Decimal("0.0000")

        actual_cost_per_unit = Decimal("0")
        if total_harvest_qty > 0:
            actual_cost_per_unit = (total_wip_incurred / total_harvest_qty).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)  # agri-guardian: decimal-safe

        # 2. Flush residual WIP to COGS (Variance Write-Off)
        if residual_wip != Decimal("0.0000"):
            desc = f"إقفال تكاليف الإنتاج (WIP Variance) للموسم - خطة: {crop_plan.name}" + (f" | مرجع: {ref_id}" if ref_id else "")
            
            if residual_wip > 0:
                # Under-absorbed (Costs > Value capitalized to Inventory)
                # Flush the remaining positive balance from WIP.
                # Debit: 6000-COGS
                # Credit: 1400-WIP
                FinanceService.post_manual_ledger_entry(
                    farm=farm,
                    account_code=FinancialLedger.ACCOUNT_COGS,
                    debit=residual_wip,
                    credit=Decimal("0.0000"),
                    description=desc,
                    user=user,
                    crop_plan=crop_plan
                )
                FinanceService.post_manual_ledger_entry(
                    farm=farm,
                    account_code=FinancialLedger.ACCOUNT_WIP,
                    debit=Decimal("0.0000"),
                    credit=residual_wip,
                    description=desc,
                    user=user,
                    crop_plan=crop_plan
                )
            else:
                # Over-absorbed (Value capitalized to Inventory > Costs) -> Negative balance
                # Flush the remaining negative balance from WIP.
                # Debit: 1400-WIP
                # Credit: 6000-COGS (Reduces COGS / Recognizes Gain)
                flush_amount = abs(residual_wip)
                FinanceService.post_manual_ledger_entry(
                    farm=farm,
                    account_code=FinancialLedger.ACCOUNT_WIP,
                    debit=flush_amount,
                    credit=Decimal("0.0000"),
                    description=desc,
                    user=user,
                    crop_plan=crop_plan
                )
                FinanceService.post_manual_ledger_entry(
                    farm=farm,
                    account_code=FinancialLedger.ACCOUNT_COGS,
                    debit=Decimal("0.0000"),
                    credit=flush_amount,
                    description=desc,
                    user=user,
                    crop_plan=crop_plan
                )

        # 3. Mark the Crop Plan as Completed
        crop_plan.status = CropPlanStatus.COMPLETED
        crop_plan.save(update_fields=['status'])

        # [AGRI-GUARDIAN §Axis-13] Mandatory AuditLog for every settlement.
        # [AGRI-GUARDIAN §Axis-13] Mandatory AuditLog for every settlement.
        from smart_agri.core.models.log import AuditLog
        AuditLog.objects.create(
            action='SEASONAL_SETTLEMENT',
            model='CropPlan',
            object_id=str(crop_plan.pk),
            actor=user,
            new_payload={
                'crop_plan_name': crop_plan.name,
                'total_harvest_qty': str(total_harvest_qty),
                'total_costs_incurred': str(total_wip_incurred),
                'actual_cost_per_unit': str(actual_cost_per_unit),
                'wip_variance_flushed': str(residual_wip),
                'farm_id': farm.pk,
                'ref_id': ref_id,
            },
        )

        return {
            "crop_plan_name": crop_plan.name,
            "total_harvest_qty": str(total_harvest_qty),
            "total_costs_incurred": str(total_wip_incurred),
            "actual_cost_per_unit": str(actual_cost_per_unit),
            "wip_variance_flushed_to_cogs": str(residual_wip)
        }
