"""
[AGRI-GUARDIAN §10] IAS 41 Biological Asset Revaluation Engine.

Implements fair-value revaluation for biological assets (trees/cohorts)
per International Accounting Standard 41 (Agriculture).

Key Principles:
- Biological assets are measured at FAIR VALUE less estimated costs to sell.
- Changes in fair value are recognized in the Financial Ledger (P&L impact).
- Revaluation is performed per-cohort, per-farm, creating paired journal entries.
- All ledger entries carry analytical dimensions (cost_center, crop_plan) per Axiom 1.
- Carrying amount is tracked via GenericFK (content_type/object_id), not text search.
"""

import logging
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.contrib.contenttypes.models import ContentType

try:
    from smart_agri.finance.services.core_finance import FinanceService
except ImportError:  # pragma: no cover - patched in tests or resolved lazily at runtime
    FinanceService = None

try:
    from smart_agri.core.services.sensitive_audit import log_sensitive_mutation
except ImportError:  # pragma: no cover - patched in tests or resolved lazily at runtime
    log_sensitive_mutation = None

logger = logging.getLogger(__name__)

# Account codes for IAS 41 revaluation journal entries
ACCOUNT_BIO_ASSET = '1600-BIO-ASSET'       # Biological Asset (Balance Sheet)
ACCOUNT_REVAL_GAIN = '5100-REVAL-GAIN'      # Fair Value Gain (Income Statement)
ACCOUNT_REVAL_LOSS = '8100-REVAL-LOSS'      # Fair Value Loss (Income Statement)


class IAS41RevaluationService:
    """
    Revalues biological asset cohorts to fair value and posts journal entries.

    Usage:
        result = IAS41RevaluationService.revalue_cohort(cohort, fair_value_per_unit, user)
        results = IAS41RevaluationService.revalue_farm(farm, valuation_map, user)
    """

    PRECISION = Decimal("0.0001")

    @staticmethod
    @transaction.atomic
    def revalue_cohort(cohort, fair_value_per_unit: Decimal, user=None, reason: str = "") -> dict:
        """
        Revalues a single BiologicalAssetCohort to fair value.

        Args:
            cohort: BiologicalAssetCohort instance.
            fair_value_per_unit: The assessed fair value per biological unit (e.g., per tree).
            user: The user performing the revaluation.
            reason: Audit reason for this revaluation.

        Returns:
            dict with revaluation details including old_value, new_value, and gain_or_loss.
        """
        finance_service = FinanceService
        if finance_service is None:  # pragma: no cover - runtime fallback if import order is incomplete
            from smart_agri.finance.services.core_finance import FinanceService as finance_service

        audit_logger = log_sensitive_mutation
        if audit_logger is None:  # pragma: no cover - runtime fallback if import order is incomplete
            from smart_agri.core.services.sensitive_audit import log_sensitive_mutation as audit_logger

        fair_value_per_unit = Decimal(str(fair_value_per_unit)).quantize(
            IAS41RevaluationService.PRECISION, rounding=ROUND_HALF_UP
        )

        quantity = Decimal(str(cohort.quantity))
        new_fair_value = (fair_value_per_unit * quantity).quantize(
            IAS41RevaluationService.PRECISION, rounding=ROUND_HALF_UP
        )

        # Determine current carrying amount from the ledger
        old_carrying_amount = IAS41RevaluationService._get_carrying_amount(cohort)

        difference = new_fair_value - old_carrying_amount

        if difference == Decimal("0.0000"):
            logger.info(
                f"IAS 41: No revaluation needed for cohort {cohort.id} "
                f"({cohort.batch_name}). Fair value unchanged at {new_fair_value}."
            )
            return {
                "cohort_id": cohort.id,
                "cohort_name": str(cohort),
                "old_value": str(old_carrying_amount),
                "new_value": str(new_fair_value),
                "difference": "0.0000",
                "action": "NO_CHANGE",
            }

        farm = cohort.farm
        description_prefix = (
            f"IAS 41 إعادة تقييم الأصول البيولوجية: {cohort.batch_name} "
            f"(الموقع: {cohort.location.name})"
        )

        # [Financial Integrity Axiom 1] Analytical Purity:
        # Derive cost_center and crop_plan from the cohort's farm context.
        cost_center = getattr(cohort, 'cost_center', None)
        crop_plan = getattr(cohort, 'crop_plan', None)

        # [D1 FIX] Use GenericFK (content_type + object_id) for structural traceability
        cohort_ct = ContentType.objects.get_for_model(cohort)

        ledger_kwargs = dict(
            farm=farm,
            user=user,
            cost_center=cost_center,
            crop_plan=crop_plan,
            content_type=cohort_ct,
            object_id=str(cohort.id),
        )

        if difference > 0:
            # Fair Value GAIN: Debit Bio Asset, Credit Revaluation Gain
            finance_service.post_manual_ledger_entry(
                account_code=ACCOUNT_BIO_ASSET,
                debit=difference,
                credit=None,
                description=f"{description_prefix} — ربح تقييم: {difference}",
                **ledger_kwargs,
            )
            finance_service.post_manual_ledger_entry(
                account_code=ACCOUNT_REVAL_GAIN,
                debit=None,
                credit=difference,
                description=f"{description_prefix} — ربح تقييم: {difference}",
                **ledger_kwargs,
            )
            action = "GAIN"
        else:
            # Fair Value LOSS: Debit Revaluation Loss, Credit Bio Asset
            loss_amount = abs(difference)
            finance_service.post_manual_ledger_entry(
                account_code=ACCOUNT_REVAL_LOSS,
                debit=loss_amount,
                credit=None,
                description=f"{description_prefix} — خسارة تقييم: {loss_amount}",
                **ledger_kwargs,
            )
            finance_service.post_manual_ledger_entry(
                account_code=ACCOUNT_BIO_ASSET,
                debit=None,
                credit=loss_amount,
                description=f"{description_prefix} — خسارة تقييم: {loss_amount}",
                **ledger_kwargs,
            )
            action = "LOSS"

        # Log the sensitive mutation for forensic audit trail
        audit_logger(
            actor=user,
            action="IAS41_REVALUATION",
            model_name="BiologicalAssetCohort",
            object_id=cohort.id,
            reason=reason or f"IAS 41 Revaluation: {action} of {abs(difference)}",
            old_value={"carrying_amount": str(old_carrying_amount)},
            new_value={"fair_value": str(new_fair_value), "per_unit": str(fair_value_per_unit)},
            farm_id=farm.id,
        )

        logger.info(
            f"IAS 41 Revaluation: Cohort={cohort.id} ({cohort.batch_name}) "
            f"Old={old_carrying_amount} New={new_fair_value} Diff={difference} Action={action}"
        )

        return {
            "cohort_id": cohort.id,
            "cohort_name": str(cohort),
            "old_value": str(old_carrying_amount),
            "new_value": str(new_fair_value),
            "difference": str(difference),
            "action": action,
        }

    @staticmethod
    @transaction.atomic  # [D4 FIX] Batch revaluation is now a single atomic transaction
    def revalue_farm(farm, valuation_map: dict, user=None) -> list:
        """
        Revalues all cohorts for a farm based on a valuation map.
        Wrapped in @transaction.atomic — all-or-nothing for financial consistency.

        Args:
            farm: Farm instance.
            valuation_map: dict mapping cohort_id -> fair_value_per_unit (Decimal).
            user: The user performing the revaluation.

        Returns:
            List of revaluation result dicts.
        """
        from smart_agri.core.models.inventory import BiologicalAssetCohort

        results = []
        cohorts = BiologicalAssetCohort.objects.filter(
            farm=farm,
            deleted_at__isnull=True,
        ).exclude(status=BiologicalAssetCohort.STATUS_EXCLUDED)

        for cohort in cohorts:
            fv = valuation_map.get(cohort.id)
            if fv is not None:
                result = IAS41RevaluationService.revalue_cohort(
                    cohort, Decimal(str(fv)), user=user,
                    reason=f"Batch revaluation for farm {farm.name}"
                )
                results.append(result)

        return results

    @staticmethod
    def _get_carrying_amount(cohort) -> Decimal:
        """
        [D1 FIX] Retrieves the current carrying amount for a cohort from the Financial Ledger.
        Uses GenericFK (content_type + object_id) for structural lookup instead of text search.
        Calculates: SUM(Debit) - SUM(Credit) for the BIO-ASSET account.
        """
        from smart_agri.finance.models import FinancialLedger
        from django.db.models import Sum

        cohort_ct = ContentType.objects.get_for_model(cohort)

        # [Axis 6] Tenant-isolated + structurally linked query
        qs = FinancialLedger.objects.filter(
            farm=cohort.farm,
            account_code=ACCOUNT_BIO_ASSET,
            content_type=cohort_ct,
            object_id=str(cohort.id),
        )

        totals = qs.aggregate(
            total_debit=Sum('debit'),
            total_credit=Sum('credit'),
        )

        debit = totals['total_debit'] or Decimal("0.0000")
        credit = totals['total_credit'] or Decimal("0.0000")

        return (debit - credit).quantize(
            IAS41RevaluationService.PRECISION, rounding=ROUND_HALF_UP
        )
