from decimal import Decimal, ROUND_HALF_UP     
from typing import Dict, List

from django.db.models import Sum

from smart_agri.core.models import Activity, ActivityCostSnapshot, CropPlan, CropPlanBudgetLine, DailyLog
from smart_agri.finance.models import CostConfiguration

def calculate_decimal_stdev(values: List[Decimal]) -> Decimal:
    """
    Manual Standard Deviation implementation using pure Decimal arithmetic.
    Avoids float conversion inherent in Python's standard statistics module.
    """
    if not values or len(values) < 2:
        return Decimal("0.00")
        
    n = Decimal(len(values))
    from decimal import getcontext
    mean = getcontext().divide(sum(values), n).quantize(Decimal("0.0001"))
    variance = getcontext().divide(sum((x - mean) ** 2 for x in values), n).quantize(Decimal("0.0001"))
    # Sqrt requires float conversion usually, but we minimize the scope or use Decimal.sqrt()
    # Decimal.sqrt() is available in standard library context
    stdev = variance.sqrt()
    return stdev.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def _decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")
    # FAIL FAST: Do not suppress errors. Bad data should crash the report generation 
    # so it can be detected and fixed, rather than falsely reporting 0 cost.
    return Decimal(value)


def compute_plan_variance(crop_plan_id: int) -> Dict:
    """Return a variance snapshot (budget vs. actual) for a given crop plan."""

    plan = CropPlan.objects.get(pk=crop_plan_id)

    budget_lines = (
        CropPlanBudgetLine.objects.filter(crop_plan=plan, deleted_at__isnull=True)
        .values("task_id", "category")
        .annotate(
            qty_budget=Sum("qty_budget"),
            total_budget=Sum("total_budget"),
        )
    )

    snapshots = ActivityCostSnapshot.objects.filter(crop_plan=plan, deleted_at__isnull=True)
    actual_totals = snapshots.aggregate(
        cost_materials=Sum("cost_materials"),
        cost_labor=Sum("cost_labor"),
        cost_machinery=Sum("cost_machinery"),
        cost_total=Sum("cost_total"),
    )

    snapshot_totals = list(snapshots.values_list("cost_total", flat=True))
    snapshot_totals_dec = [_decimal(total) for total in snapshot_totals]
    std_dev = calculate_decimal_stdev(snapshot_totals_dec)

    by_task: List[Dict] = []
    actual_by_task = (
        snapshots.values("task_id")
        .annotate(
            cost_materials=Sum("cost_materials"),
            cost_labor=Sum("cost_labor"),
            cost_machinery=Sum("cost_machinery"),
            cost_total=Sum("cost_total"),
        )
        .order_by()
    )
    budget_by_task = { (row["task_id"], row["category"]): row for row in budget_lines }

    for row in actual_by_task:
        task_id = row["task_id"]
        budget_materials = _decimal(budget_by_task.get((task_id, CropPlanBudgetLine.CATEGORY_MATERIALS), {}).get("total_budget"))
        budget_labor = _decimal(budget_by_task.get((task_id, CropPlanBudgetLine.CATEGORY_LABOR), {}).get("total_budget"))
        budget_machinery = _decimal(budget_by_task.get((task_id, CropPlanBudgetLine.CATEGORY_MACHINERY), {}).get("total_budget"))
        by_task.append(
            {
                "task_id": task_id,
                "budget_materials": budget_materials,
                "budget_labor": budget_labor,
                "budget_machinery": budget_machinery,
                "budget_total": budget_materials + budget_labor + budget_machinery,
                "actual_materials": _decimal(row["cost_materials"]),
                "actual_labor": _decimal(row["cost_labor"]),
                "actual_machinery": _decimal(row["cost_machinery"]),
                "actual_total": _decimal(row["cost_total"]),
            }
        )

    response = {
        "plan_id": plan.pk,
        "currency": plan.currency,
        "budget": {
            "materials": _decimal(plan.budget_materials),
            "labor": _decimal(plan.budget_labor),
            "machinery": _decimal(plan.budget_machinery),
            "total": _decimal(plan.budget_total),
        },
        "actual": {
            "materials": _decimal(actual_totals.get("cost_materials")),
            "labor": _decimal(actual_totals.get("cost_labor")),
            "machinery": _decimal(actual_totals.get("cost_machinery")),
            "total": _decimal(actual_totals.get("cost_total")),
        },
        "std_dev_total": std_dev,
        "tasks": by_task,
    }

    return response


def compute_log_variance(log: DailyLog) -> Dict:
    """
    Compute variance for a DailyLog across all crop plans in the log.
    Returns status + max deviation percent and per-plan details.
    """
    activities = log.activities.filter(
        deleted_at__isnull=True, crop_plan__isnull=False
    ).select_related('crop_plan')
    if not activities.exists():
        return {
            "status": "OK",
            "max_deviation_pct": Decimal("0.00"),
            "details": [],
        }

    config = CostConfiguration.objects.filter(farm=log.farm, deleted_at__isnull=True).first()
    warning_threshold = (config.variance_warning_pct if config else Decimal("10.00"))
    critical_threshold = (config.variance_critical_pct if config else Decimal("20.00"))

    details = []
    max_deviation = Decimal("0.00")
    status = "OK"

    plans = activities.values_list("crop_plan_id", flat=True).distinct()
    for plan_id in plans:
        plan = CropPlan.objects.filter(pk=plan_id).first()
        if not plan:
            continue
        actual_total = activities.filter(crop_plan_id=plan_id).aggregate(
            total=Sum("cost_total")
        )["total"] or Decimal("0.00")
        budget_total = _decimal(plan.budget_total)
        if budget_total == 0:
            deviation_pct = Decimal("100.00") if actual_total > 0 else Decimal("0.00")
        else:
            deviation_pct = ((actual_total - budget_total) / budget_total * Decimal("100.00")).quantize(  # agri-guardian: decimal-safe
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )
        max_deviation = max(max_deviation, abs(deviation_pct))
        if abs(deviation_pct) >= critical_threshold:
            status = "CRITICAL"
        elif abs(deviation_pct) >= warning_threshold and status != "CRITICAL":
            status = "WARNING"

        details.append({
            "crop_plan_id": plan_id,
            "budget_total": budget_total,
            "actual_total": actual_total,
            "deviation_pct": deviation_pct,
        })

    return {
        "status": status,
        "max_deviation_pct": max_deviation,
        "details": details,
        "thresholds": {
            "warning_pct": warning_threshold,
            "critical_pct": critical_threshold,
        },
    }


def detect_cost_anomalies(crop_plan_id: int) -> List[Dict]:
    """
    Analyze activities for a plan and detect cost anomalies using Mean + 2*StdDev.
    """
    plan = CropPlan.objects.get(pk=crop_plan_id)
    activities = list(
        Activity.objects.filter(crop_plan=plan, deleted_at__isnull=True).select_related('task', 'log')
    )

    def _effective_total(activity: Activity) -> Decimal:
        cost_total = Decimal(activity.cost_total or 0)
        if cost_total > 0:
            return cost_total

        subtotal = (
            Decimal(activity.cost_materials or 0)
            + Decimal(activity.cost_labor or 0)
            + Decimal(activity.cost_machinery or 0)
            + Decimal(activity.cost_overhead or 0)
        )

        # Legacy fallback: derive overhead from planted_area payload when no snapshot exists yet.
        planted_area = Decimal("0")
        planted_uom = "ha"
        data = activity.data if isinstance(activity.data, dict) else {}
        if data.get("planted_area") is not None:
            planted_area = _decimal(data.get("planted_area"))
            planted_uom = str(data.get("planted_uom") or "ha").lower()
        from decimal import getcontext
        # Convert to hectares based on UOM (Yemeni-relevant units)
        if planted_uom == "m2":
            area_ha = getcontext().divide(planted_area, Decimal("10000"))
        elif planted_uom in ("dunum", "dunums"):
            area_ha = getcontext().divide(planted_area, Decimal("10"))
        elif planted_uom == "libnah":
            area_ha = getcontext().divide(planted_area * Decimal("44.4"), Decimal("10000"))
        else:
            area_ha = planted_area  # assume hectares
        if area_ha <= 0:
            return subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        farm_id = getattr(activity.log, "farm_id", None)
        overhead_rate = Decimal("50.00")
        if farm_id:
            config = CostConfiguration.objects.filter(farm_id=farm_id, deleted_at__isnull=True).first()
            if config and config.overhead_per_hectare is not None:
                overhead_rate = _decimal(config.overhead_per_hectare)
        derived_overhead = (area_ha * overhead_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if Decimal(activity.cost_overhead or 0) > 0:
            return subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return (subtotal + derived_overhead).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    costs = [_effective_total(a) for a in activities]
    if not costs:
        return []
    from decimal import getcontext
    mean = getcontext().divide(sum(costs), Decimal(len(costs))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    stdev = calculate_decimal_stdev(costs)
    if stdev == 0:
        return []

    threshold = mean + (Decimal("2.0") * stdev)

    anomalies = []
    for activity in activities:
        cost = _effective_total(activity)
        if cost <= threshold:
            continue
        from decimal import getcontext
        risk_score = getcontext().divide(cost - mean, stdev).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        anomalies.append({
            "activity_id": activity.pk,
            "task_name": activity.task.name if activity.task else "Unknown",
            "date": activity.log.log_date if activity.log else "N/A",
            "cost_total": cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            "mean": mean,
            "threshold": threshold.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            "deviation": (cost - mean).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            "risk_score": risk_score,
        })
    return anomalies


# ─────────────────────────────────────────────────────────────────────────────
# [AGRI-GUARDIAN] Sprint 3 — Extended Variance Controls
# ─────────────────────────────────────────────────────────────────────────────

def compute_schedule_variance(crop_plan_id: int) -> Dict:
    """
    [AGRI-GUARDIAN Axis 6] Schedule Variance.
    Compares planned activity dates vs actual execution dates.
    Detects slippage (late starts) and schedule compression.
    """
    from smart_agri.core.models import CropPlanBudgetLine

    plan = CropPlan.objects.get(pk=crop_plan_id)
    budget_lines = CropPlanBudgetLine.objects.filter(
        crop_plan=plan, deleted_at__isnull=True
    ).select_related("task")

    activities = Activity.objects.filter(
        crop_plan=plan, deleted_at__isnull=True
    ).select_related("task", "log")

    task_schedule: Dict = {}
    for bl in budget_lines:
        if bl.task_id and hasattr(bl, "planned_start"):
            planned_start = getattr(bl, "planned_start", None)
            if planned_start:
                task_schedule[bl.task_id] = {"planned_start": planned_start}

    variances = []
    for activity in activities:
        actual_date = activity.log.log_date if activity.log else None
        if not actual_date or not activity.task_id:
            continue
        sched = task_schedule.get(activity.task_id)
        if not sched:
            continue
        planned = sched["planned_start"]
        delta_days = (actual_date - planned).days
        status = "OK"
        if delta_days > 7:
            status = "CRITICAL"
        elif delta_days > 3:
            status = "WARNING"

        variances.append({
            "task_id": activity.task_id,
            "activity_id": activity.pk,
            "planned_date": str(planned),
            "actual_date": str(actual_date),
            "slippage_days": delta_days,
            "status": status,
        })

    overall = "OK"
    if any(v["status"] == "CRITICAL" for v in variances):
        overall = "CRITICAL"
    elif any(v["status"] == "WARNING" for v in variances):
        overall = "WARNING"

    return {
        "plan_id": crop_plan_id,
        "overall_status": overall,
        "task_variances": variances,
    }


def compute_yield_variance(crop_plan_id: int) -> Dict:
    """
    [AGRI-GUARDIAN Axis 6] Yield Variance.
    Compares expected yield (from CropPlan) vs actual harvest quantities.
    """
    from smart_agri.core.models import ActivityHarvest

    plan = CropPlan.objects.get(pk=crop_plan_id)
    expected_yield = _decimal(plan.expected_yield)

    harvest_activities = Activity.objects.filter(
        crop_plan=plan, deleted_at__isnull=True
    )
    actual_harvests = ActivityHarvest.objects.filter(
        activity__in=harvest_activities
    )
    actual_total = actual_harvests.aggregate(
        total=Sum("harvest_quantity")
    )["total"] or Decimal("0")

    if expected_yield > 0:
        from decimal import getcontext
        deviation_pct = (
            getcontext().divide(actual_total - expected_yield, expected_yield) * Decimal("100.00")
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    else:
        deviation_pct = Decimal("0.00")

    status = "OK"
    if abs(deviation_pct) >= Decimal("30.00"):
        status = "CRITICAL"
    elif abs(deviation_pct) >= Decimal("15.00"):
        status = "WARNING"

    return {
        "plan_id": crop_plan_id,
        "expected_yield": expected_yield,
        "actual_yield": actual_total,
        "deviation_pct": deviation_pct,
        "status": status,
    }


def compute_material_variance(crop_plan_id: int) -> Dict:
    """
    [AGRI-GUARDIAN Axis 6] Material Variance.
    Per-category budget vs actual comparison with threshold alerts.
    """
    plan = CropPlan.objects.get(pk=crop_plan_id)
    config = CostConfiguration.objects.filter(
        farm=plan.farm, deleted_at__isnull=True
    ).first()
    warning_pct = _decimal(getattr(config, "variance_warning_pct", None)) or Decimal("10.00")
    critical_pct = _decimal(getattr(config, "variance_critical_pct", None)) or Decimal("20.00")

    snapshots = ActivityCostSnapshot.objects.filter(
        crop_plan=plan, deleted_at__isnull=True
    )
    actual = snapshots.aggregate(
        materials=Sum("cost_materials"),
        labor=Sum("cost_labor"),
        machinery=Sum("cost_machinery"),
    )

    categories = []
    for category, budget_field, actual_key in [
        ("materials", "budget_materials", "materials"),
        ("labor", "budget_labor", "labor"),
        ("machinery", "budget_machinery", "machinery"),
    ]:
        budget_val = _decimal(getattr(plan, budget_field, None))
        actual_val = _decimal(actual.get(actual_key))
        if budget_val > 0:
            from decimal import getcontext
            dev_pct = (getcontext().divide(actual_val - budget_val, budget_val) * Decimal("100.00")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        else:
            dev_pct = Decimal("100.00") if actual_val > 0 else Decimal("0.00")

        cat_status = "OK"
        if abs(dev_pct) >= critical_pct:
            cat_status = "CRITICAL"
        elif abs(dev_pct) >= warning_pct:
            cat_status = "WARNING"

        categories.append({
            "category": category,
            "budget": budget_val,
            "actual": actual_val,
            "deviation_pct": dev_pct,
            "status": cat_status,
        })

    overall = "OK"
    if any(c["status"] == "CRITICAL" for c in categories):
        overall = "CRITICAL"
    elif any(c["status"] == "WARNING" for c in categories):
        overall = "WARNING"

    return {
        "plan_id": crop_plan_id,
        "overall_status": overall,
        "categories": categories,
        "thresholds": {
            "warning_pct": warning_pct,
            "critical_pct": critical_pct,
        },
    }
