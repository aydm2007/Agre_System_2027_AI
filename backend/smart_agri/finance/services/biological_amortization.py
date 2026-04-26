import logging
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger(__name__)

class BiologicalAmortizationService:
    """
    [AGRI-GUARDIAN Phase 6] Biological Asset Amortization.
    Transitions WIP costs into a structured Depreciation Expense schedule
    once a tree cohort flips to PRODUCTIVE.
    """

    @staticmethod
    @transaction.atomic
    def amortize_productive_cohorts(farm, user=None, period_date=None, ref_id=""):
        """
        Runs the periodic amortization (depreciation) for all PRODUCTIVE cohorts in a farm.
        """
        from smart_agri.finance.models import FinancialLedger
        from smart_agri.finance.services.core_finance import FinanceService
        from smart_agri.core.models.inventory import BiologicalAssetCohort

        period_date = period_date or timezone.now().date()
        FinanceService.check_fiscal_period(period_date, farm)

        cohorts = BiologicalAssetCohort.objects.filter(
            farm=farm,
            status=BiologicalAssetCohort.STATUS_PRODUCTIVE
        )

        results = []
        cohort_ctype = ContentType.objects.get_for_model(BiologicalAssetCohort)

        for cohort in cohorts:
            # 1. Capitalize WIP to Biological Asset if not already done.
            carrying_value = BiologicalAmortizationService._capitalize_wac_to_asset(cohort, farm, user, period_date, cohort_ctype)

            if carrying_value <= Decimal("0"):
                continue

            # 2. Amortize the Biological Asset over its useful life.
            # Assume a default standard (e.g., 20 years = 240 months).
            useful_life_months = Decimal("240")
            
            # Simple straight-line monthly depreciation
            monthly_depreciation = (carrying_value / useful_life_months).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)  # agri-guardian: decimal-safe
            
            if monthly_depreciation <= Decimal("0"):
                continue

            desc = f"إهلاك الأصول الحيوية الشهري - {cohort.batch_name}" + (f" | مرجع: {ref_id}" if ref_id else "")

            # Post the amortization entry
            # Debit: 7000-DEP-EXP (Depreciation Expense)
            FinanceService.post_manual_ledger_entry(
                farm=farm,
                account_code=FinancialLedger.ACCOUNT_DEPRECIATION_EXPENSE,
                debit=monthly_depreciation,
                credit=Decimal("0.0000"),
                description=desc,
                user=user,
                content_type=cohort_ctype,
                object_id=str(cohort.id)
            )

            # Credit: 1500-ACC-DEP (Accumulated Depreciation)
            FinanceService.post_manual_ledger_entry(
                farm=farm,
                account_code=FinancialLedger.ACCOUNT_ACCUM_DEPRECIATION,
                debit=Decimal("0.0000"),
                credit=monthly_depreciation,
                description=desc,
                user=user,
                content_type=cohort_ctype,
                object_id=str(cohort.id)
            )

            results.append({
                "cohort_id": str(cohort.id),
                "batch_name": cohort.batch_name,
                "amortized_amount": str(monthly_depreciation)
            })

        return results

    @staticmethod
    def _capitalize_wac_to_asset(cohort, farm, user, period_date, cohort_ctype) -> Decimal:
        """
        Transfers WIP costs to BIO-ASSET when cohort becomes productive.
        Returns the updated carrying VALUE of BIO-ASSET.
        """
        from smart_agri.finance.models import FinancialLedger
        from django.db.models import Sum, F
        from smart_agri.finance.services.core_finance import FinanceService

        ACCOUNT_BIO_ASSET = '1600-BIO-ASSET' # Must match ias41_revaluation.py conventions
        
        # Calculate uncapitalized WIP
        wip_qs = FinancialLedger.objects.filter(
            farm=farm,
            account_code=FinancialLedger.ACCOUNT_WIP,
            content_type=cohort_ctype,
            object_id=str(cohort.id)
        ).aggregate(balance=Sum(F('debit') - F('credit')))
        
        uncapitalized_wip = wip_qs.get('balance') or Decimal("0.0000")

        if uncapitalized_wip > Decimal("0"):
            desc = f"رسملة تكاليف تحت الإنجاز للأصل الحيوي - {cohort.batch_name}"
            # Credit: 1400-WIP
            FinanceService.post_manual_ledger_entry(
                farm=farm,
                account_code=FinancialLedger.ACCOUNT_WIP,
                debit=Decimal("0.0000"),
                credit=uncapitalized_wip,
                description=desc,
                user=user,
                content_type=cohort_ctype,
                object_id=str(cohort.id)
            )
            # Debit: 1600-BIO-ASSET
            FinanceService.post_manual_ledger_entry(
                farm=farm,
                account_code=ACCOUNT_BIO_ASSET,
                debit=uncapitalized_wip,
                credit=Decimal("0.0000"),
                description=desc,
                user=user,
                content_type=cohort_ctype,
                object_id=str(cohort.id)
            )

        # Retrieve net carrying amount of BIO-ASSET
        bio_asset_qs = FinancialLedger.objects.filter(
            farm=farm,
            account_code=ACCOUNT_BIO_ASSET,
            content_type=cohort_ctype,
            object_id=str(cohort.id)
        ).aggregate(balance=Sum(F('debit') - F('credit')))
        
        return bio_asset_qs.get('balance') or Decimal("0.0000")
