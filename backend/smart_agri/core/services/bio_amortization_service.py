"""
BiologicalAmortizationService — إهلاك الأصول البيولوجية المعمرة.

Runs monthly amortization for PRODUCTIVE perennial cohorts:
  - Calculates monthly portion based on useful life
  - Posts: DR 7000-DEP-EXP / CR 1600-BIO-ASSET

AGENTS.md Compliance:
  - Axis 5: Decimal(19,4)
  - Axis 6: Farm-scoped
  - Axis 7: AuditLog
  - Axis 11: Biological Asset Hierarchy — PRODUCTIVE = OPEX
"""

import logging
from decimal import Decimal
from datetime import date

from django.db import transaction
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

FOUR_DP = Decimal("0.0001")
ZERO = Decimal("0.0000")
TWELVE = Decimal("12")

# Default useful life for perennial crops (years)
DEFAULT_USEFUL_LIFE_YEARS = 25


class BiologicalAmortizationService:
    """
    [AGENTS.md Axis 11] Monthly amortization for PRODUCTIVE biological cohorts.
    JUVENILE cohorts are capitalized (no depreciation).
    PRODUCTIVE cohorts are OPEX — monthly depreciation.
    """

    @staticmethod
    @transaction.atomic
    def run_monthly_amortization(*, farm_id, year, month, user=None):
        """
        Process depreciation for all PRODUCTIVE cohorts in a farm.
        Returns list of depreciation entries posted.
        """
        from smart_agri.core.models.inventory import BiologicalAssetCohort
        from smart_agri.finance.models import FinancialLedger

        if not farm_id:
            raise ValidationError({"farm_id": "[Axis 6] معرف المزرعة مطلوب."})

        # [Axis 2] Idempotency — check if already run for this period
        alloc_marker = f"bio-amort-{farm_id}-{year}-{month:02d}"
        if FinancialLedger.objects.filter(
            farm_id=farm_id,
            description__contains=alloc_marker,
        ).exists():
            logger.info("Bio amortization already run for %s/%s farm=%s.", year, month, farm_id)
            return {"status": "already_processed", "period": f"{year}-{month:02d}"}

        # Get all PRODUCTIVE cohorts for this farm
        productive_cohorts = BiologicalAssetCohort.objects.filter(
            farm_id=farm_id,
            status=BiologicalAssetCohort.STATUS_PRODUCTIVE,
            deleted_at__isnull=True,
            quantity__gt=0,
        ).select_related('crop', 'variety')

        if not productive_cohorts.exists():
            return {"status": "no_cohorts", "period": f"{year}-{month:02d}"}

        results = []
        created_by = user if user and getattr(user, 'is_authenticated', False) else None

        for cohort in productive_cohorts:
            # Calculate monthly depreciation using model fields
            useful_life_years = Decimal(str(cohort.useful_life_years or DEFAULT_USEFUL_LIFE_YEARS))
            total_months = useful_life_years * TWELVE

            # Cost basis from capitalized_cost field (set at JUVENILE→PRODUCTIVE transition)
            cost_basis = Decimal(str(cohort.capitalized_cost or 0)).quantize(FOUR_DP)
            if cost_basis <= ZERO:
                # [FIX] Use cohort-level configurable fallback instead of hardcoded 500
                fallback_cost = Decimal(str(
                    cohort.default_planting_cost or
                    getattr(cohort.variety, 'planting_cost_per_unit', None) or
                    500
                ))
                cost_basis = (Decimal(str(cohort.quantity)) * fallback_cost).quantize(FOUR_DP)

            monthly_depreciation = (cost_basis / total_months).quantize(FOUR_DP)  # agri-guardian: decimal-safe
            if monthly_depreciation <= ZERO:
                continue

            cohort_label = f"{cohort.crop.name if cohort.crop else ''} — {cohort.batch_name}"

            # Post double-entry: DR Depreciation Expense / CR Bio-Asset
            FinancialLedger.objects.create(
                farm_id=farm_id,
                account_code='7000-DEP-EXP',
                debit=monthly_depreciation,
                credit=ZERO,
                description=(
                    f"إهلاك بيولوجي شهري — {cohort_label} "
                    f"({monthly_depreciation}/{total_months} شهر) [{alloc_marker}]"
                ),
                created_by=created_by,
            )
            FinancialLedger.objects.create(
                farm_id=farm_id,
                account_code='1600-BIO-ASSET',
                debit=ZERO,
                credit=monthly_depreciation,
                description=(
                    f"تخفيض أصل بيولوجي — {cohort_label} [{alloc_marker}]"
                ),
                created_by=created_by,
            )

            # [FIX] Track accumulated depreciation on the cohort itself
            cohort.accumulated_depreciation = (
                Decimal(str(cohort.accumulated_depreciation or 0)) + monthly_depreciation
            ).quantize(FOUR_DP)
            cohort.save(update_fields=["accumulated_depreciation"])

            results.append({
                "cohort_id": cohort.id,
                "cohort_name": cohort_label,
                "cost_basis": str(cost_basis),
                "monthly_depreciation": str(monthly_depreciation),
                "accumulated_depreciation": str(cohort.accumulated_depreciation),
                "useful_life_months": str(total_months),
            })

        # [Axis 7] AuditLog
        from smart_agri.core.models.log import AuditLog
        AuditLog.objects.create(
            action='BIO_AMORTIZATION',
            model='BiologicalAssetCohort',
            object_id=alloc_marker,
            actor=user,
            new_payload={
                'period': f"{year}-{month:02d}",
                'cohorts_processed': len(results),
                'farm_id': farm_id,
            },
        )

        logger.info(
            "Bio amortization: farm=%s, period=%s-%02d, cohorts=%d",
            farm_id, year, month, len(results),
        )

        return {
            "status": "processed",
            "period": f"{year}-{month:02d}",
            "cohorts_count": len(results),
            "cohorts": results,
        }
