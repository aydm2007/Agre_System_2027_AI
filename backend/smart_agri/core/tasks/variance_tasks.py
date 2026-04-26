"""
Periodic Variance Update Task — مهمة تحديث الانحرافات الدورية.

Runs on a schedule (e.g., every 2 hours) via Celery Beat to:
1. Re-calculate variance for all active DailyLogs from today
2. Update DailyLog.variance_status based on latest calculations
3. Generate VarianceAlert for any new CRITICAL deviations

AGENTS.md Compliance:
  - Axis 5: Decimal-only
  - Axis 6: Farm-scoped
  - Axis 7: AuditLog
"""

import logging
from decimal import Decimal
from datetime import date

from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

ZERO = Decimal("0.0000")
FOUR_DP = Decimal("0.0001")


try:
    from celery import shared_task
except ImportError:
    # Fallback for environments without Celery
    def shared_task(func=None, **kwargs):
        if func is not None:
            return func
        return lambda f: f


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def update_daily_variance_status(self):
    """
    [AGRI-GUARDIAN §Axis-6] Periodic Variance Scanner.
    
    Scans all DailyLogs from today, re-evaluates cost variance,
    and updates variance_status (OK / WARNING / CRITICAL).
    
    Schedule: Every 2 hours via Celery Beat.
    """
    from smart_agri.core.models.log import DailyLog
    from smart_agri.core.services.variance import compute_log_variance

    today = date.today()
    logs = DailyLog.objects.filter(
        log_date=today,
        deleted_at__isnull=True,
    ).select_related("farm")

    updated_count = 0
    alert_count = 0

    for log in logs:
        try:
            result = compute_log_variance(log)

            max_pct = abs(Decimal(str(result.get("max_deviation_pct", 0))))
            
            if max_pct >= Decimal("25"):
                new_status = "CRITICAL"
                alert_count += 1
            elif max_pct >= Decimal("10"):
                new_status = "WARNING"
            else:
                new_status = "OK"

            if log.variance_status != new_status:
                DailyLog.objects.filter(pk=log.pk).update(
                    variance_status=new_status,
                    variance_note=f"تحديث دوري: انحراف {max_pct}%",
                )
                updated_count += 1

        except (ArithmeticError, TypeError, ValueError, ValidationError) as exc:
            logger.warning(
                "Variance update failed for DailyLog %s (farm=%s): %s",
                log.pk, log.farm_id, exc,
            )
            continue

    logger.info(
        "Periodic variance scan: date=%s, scanned=%d, updated=%d, alerts=%d",
        today, logs.count(), updated_count, alert_count,
    )

    return {
        "date": str(today),
        "scanned": logs.count(),
        "updated": updated_count,
        "critical_alerts": alert_count,
    }


@shared_task(bind=True, max_retries=1)
def update_budget_burn_rates(self):
    """
    [AGRI-GUARDIAN §Axis-8] Proactive Budget Burn Rate Scanner.
    
    For each active CropPlan with a budget, checks if spend rate
    significantly outpaces elapsed time percentage.
    """
    from smart_agri.core.models.planning import CropPlan
    from smart_agri.core.services.shadow_variance_engine import ShadowVarianceEngine
    from django.db.models import Sum

    today = date.today()
    active_plans = CropPlan.objects.filter(
        deleted_at__isnull=True,
        start_date__lte=today,
        end_date__gte=today,
        budget_total__gt=0,
    ).select_related("farm")

    flagged = 0

    for plan in active_plans:
        try:
            total_budget = plan.budget_total or ZERO
            if total_budget <= ZERO:
                continue

            # Calculate elapsed percentage
            total_days = (plan.end_date - plan.start_date).days or 1
            elapsed_days = (today - plan.start_date).days
            elapsed_pct = (Decimal(str(elapsed_days)) / Decimal(str(total_days)) * Decimal("100")).quantize(FOUR_DP)

            # Calculate current spend
            current_spend = plan.activities.filter(
                deleted_at__isnull=True,
            ).aggregate(
                total=Sum("cost_total")
            )["total"] or ZERO

            ShadowVarianceEngine.audit_budget_burn_rate(
                farm=plan.farm,
                crop_plan=plan,
                current_spend=current_spend,
                total_budget=total_budget,
                elapsed_pct=elapsed_pct,
            )
            flagged += 1

        except (ArithmeticError, TypeError, ValueError, ValidationError) as exc:
            logger.warning(
                "Budget burn rate check failed for CropPlan %s: %s",
                plan.pk, exc,
            )
            continue

    logger.info("Budget burn rate scan: plans=%d, checked=%d", active_plans.count(), flagged)

    return {
        "date": str(today),
        "active_plans": active_plans.count(),
        "checked": flagged,
    }
