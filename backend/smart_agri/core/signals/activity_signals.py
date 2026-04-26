"""
Activity Post-Save Signals — إشارات ما بعد حفظ النشاط.

Automatically triggers:
1. Variance calculation via ShadowVarianceEngine after each Activity save
2. WIP (Work-in-Progress) ledger posting for activity costs

AGENTS.md Compliance:
  - Axis 5: Decimal-only
  - Axis 6: Farm-scoped
  - Axis 7: AuditLog for auto-postings
"""

import hashlib
import logging
from decimal import Decimal

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)

ZERO = Decimal("0.0000")
FOUR_DP = Decimal("0.0001")


def _ledger_signature(activity, cost_total: Decimal) -> str:
    payload = f"{activity.pk}|{activity.crop_plan_id or ''}|{cost_total.quantize(FOUR_DP)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


@receiver(post_save, sender="core.Activity")
def activity_post_save_handler(sender, instance, created, **kwargs):
    """
    [AGRI-GUARDIAN] Auto-trigger after Activity save:
    1. Run ShadowVarianceEngine.audit_execution_cost() — compares actual vs plan
    2. Post WIP journal entry to FinancialLedger — DR WIP / CR Accrued Liability
    """
    # Avoid circular imports
    from smart_agri.core.services.shadow_variance_engine import ShadowVarianceEngine
    from smart_agri.finance.models import FinancialLedger

    activity = instance

    # --- Guard: Only process if activity has a cost and a farm ---
    cost_total = activity.cost_total or ZERO
    if cost_total <= ZERO:
        return

    farm = None
    if activity.log_id:
        try:
            farm = activity.log.farm
        except (AttributeError, LookupError):
            pass

    if not farm:
        return

    # --- 1. Auto-Variance Calculation ---
    planned_cost = ZERO
    if activity.crop_plan_id:
        from smart_agri.core.models.planning import CropPlanBudgetLine
        budget = CropPlanBudgetLine.objects.filter(
            crop_plan_id=activity.crop_plan_id,
            task=activity.task,
            deleted_at__isnull=True,
        ).first()
        if budget:
            planned_cost = budget.total_budget or ZERO

    if planned_cost > ZERO:
        ShadowVarianceEngine.audit_execution_cost(
            farm=farm,
            activity_name=str(activity.task or "نشاط"),
            actual_cost=cost_total,
            planned_cost=planned_cost,
            daily_log=activity.log if activity.log_id else None,
        )
        logger.info(
            "Auto-variance: activity=%s, actual=%s, planned=%s",
            activity.pk, cost_total, planned_cost,
        )

    # --- 2. Auto WIP Ledger Posting ---
    base_key = f"WIP_AUTO_{activity.pk}"
    posting_key = f"{base_key}_{_ledger_signature(activity, cost_total)}"
    liability_key = f"LIA_{posting_key}"

    existing = FinancialLedger.objects.filter(
        farm=farm,
        idempotency_key__startswith=f"{base_key}_",
    ).order_by("-created_at").first()
    existing_liability = FinancialLedger.objects.filter(
        farm=farm,
        idempotency_key__startswith=f"LIA_{base_key}_",
    ).order_by("-created_at").first()

    if (
        existing
        and existing_liability
        and existing.debit == cost_total
        and existing_liability.credit == cost_total
    ):
        return

    if existing and not FinancialLedger.objects.filter(idempotency_key=f"REV_{existing.idempotency_key}").exists():
        FinancialLedger.objects.create(
            farm=farm,
            activity=activity,
            crop_plan=activity.crop_plan,
            account_code=FinancialLedger.ACCOUNT_WIP,
            debit=ZERO,
            credit=existing.debit,
            description=f"[عكس WIP] نشاط #{activity.pk}",
            idempotency_key=f"REV_{existing.idempotency_key}",
        )

    if existing_liability and not FinancialLedger.objects.filter(idempotency_key=f"REV_{existing_liability.idempotency_key}").exists():
        FinancialLedger.objects.create(
            farm=farm,
            activity=activity,
            crop_plan=activity.crop_plan,
            account_code=FinancialLedger.ACCOUNT_ACCRUED_LIABILITY,
            debit=existing_liability.credit,
            credit=ZERO,
            description=f"[عكس التزام] نشاط #{activity.pk}",
            idempotency_key=f"REV_{existing_liability.idempotency_key}",
        )

    if not FinancialLedger.objects.filter(farm=farm, idempotency_key=posting_key).exists():
        FinancialLedger.objects.create(
            farm=farm,
            activity=activity,
            crop_plan=activity.crop_plan,
            account_code=FinancialLedger.ACCOUNT_WIP,
            debit=cost_total,
            credit=ZERO,
            description=f"WIP تلقائي — نشاط #{activity.pk} ({activity.task or 'عام'})",
            idempotency_key=posting_key,
        )

    if not FinancialLedger.objects.filter(farm=farm, idempotency_key=liability_key).exists():
        FinancialLedger.objects.create(
            farm=farm,
            activity=activity,
            crop_plan=activity.crop_plan,
            account_code=FinancialLedger.ACCOUNT_ACCRUED_LIABILITY,
            debit=ZERO,
            credit=cost_total,
            description=f"التزام مستحق — نشاط #{activity.pk} ({activity.task or 'عام'})",
            idempotency_key=liability_key,
        )

    logger.info(
        "Auto WIP posted: activity=%s, cost=%s, farm=%s",
        activity.pk, cost_total, farm.pk,
    )
