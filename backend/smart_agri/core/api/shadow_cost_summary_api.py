"""
Shadow Cost Summary API — ملخص التكلفة الظلية للمود البسيط.

[AGRI-GUARDIAN V21 — Shadow Accounting Doctrine, PRD §7.2 / §10]
================================================================

PURPOSE:
    This API provides SIMPLE mode users with cost awareness WITHOUT ledger posting.
    In SIMPLE mode, Activity costs are "shadow" computed values — they show what
    things cost for operational awareness, but they do NOT create FinancialLedger
    entries or TreasuryTransactions.

TRUTH CHAIN:
    CropPlan → DailyLog → Activity → CostingService → shadow fields on Activity
    (cost_labor, cost_materials, cost_machinery, cost_overhead, cost_total)
    
    These fields are written by CostingService.calculate_activity_cost() which
    works in BOTH modes. The boundary is:
    - SIMPLE: shadow fields populated, NO ledger entries
    - STRICT: shadow fields populated + FinancialLedger entries + Treasury

RELATED:
    - burn_rate_summary: plan-level budget burn percentages (no absolutes)
    - shadow_cost_summary: activity-level cost breakdown (proportional only)
    
SECURITY:
    - Only percentages and status indicators in SIMPLE mode
    - Absolute values only visible when farm is in STRICT mode
"""

import logging
from decimal import Decimal

from django.db.models import Sum, Count, Q
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from smart_agri.core.api.permissions import _ensure_user_has_farm_access
from smart_agri.core.models.settings import FarmSettings

logger = logging.getLogger(__name__)

ZERO = Decimal("0.0000")
FOUR_DP = Decimal("0.0001")


def _safe_pct(part, whole):
    """Decimal-safe percentage."""
    if not whole or whole <= ZERO:
        return ZERO
    return ((part / whole) * Decimal("100")).quantize(FOUR_DP)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def shadow_cost_summary(request):
    """
    GET /api/v1/shadow-cost-summary/?farm=<farm_id>&crop_plan=<crop_plan_id>

    Returns a shadow cost breakdown for the specified farm/crop plan.

    SIMPLE mode response (percentages only):
    {
        "mode": "SIMPLE",
        "total_activities": 42,
        "costed_activities": 38,
        "costing_coverage_pct": "90.4762",
        "cost_breakdown_pct": {
            "labor_pct": "45.0000",
            "materials_pct": "30.2000",
            "machinery_pct": "15.8000",
            "overhead_pct": "9.0000"
        },
        "top_expense_category": "labor",
        "shadow_health": "GREEN"
    }

    STRICT mode response (includes absolute values):
    {
        "mode": "STRICT",
        ... same as above plus ...
        "total_cost": "125000.0000",
        "cost_labor": "56250.0000",
        "cost_materials": "37750.0000",
        "cost_machinery": "19750.0000",
        "cost_overhead": "11250.0000"
    }
    """
    farm_id = request.query_params.get('farm')
    crop_plan_id = request.query_params.get('crop_plan')

    if not farm_id:
        return Response(
            {"detail": "معرّف المزرعة مطلوب (?farm=X)."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        farm_id = int(farm_id)
    except (ValueError, TypeError):
        return Response(
            {"detail": "معرّف المزرعة غير صالح."},
            status=status.HTTP_400_BAD_REQUEST
        )

    _ensure_user_has_farm_access(request.user, farm_id)

    # Determine mode
    try:
        settings = FarmSettings.objects.filter(farm_id=farm_id).first()
        mode = getattr(settings, 'mode', FarmSettings.MODE_SIMPLE) if settings else FarmSettings.MODE_SIMPLE
    except (ValueError, TypeError, AttributeError):
        mode = FarmSettings.MODE_SIMPLE

    # Query activity costs
    from smart_agri.core.models.activity import Activity

    qs = Activity.objects.filter(
        log__farm_id=farm_id,
        deleted_at__isnull=True,
    )
    if crop_plan_id:
        qs = qs.filter(crop_plan_id=crop_plan_id)

    agg = qs.aggregate(
        total_count=Count('id'),
        costed_count=Count('id', filter=Q(cost_total__isnull=False, cost_total__gt=ZERO)),
        sum_labor=Sum('cost_labor'),
        sum_materials=Sum('cost_materials'),
        sum_machinery=Sum('cost_machinery'),
        sum_overhead=Sum('cost_overhead'),
        sum_total=Sum('cost_total'),
    )

    total_count = agg['total_count'] or 0
    costed_count = agg['costed_count'] or 0
    sum_labor = agg['sum_labor'] or ZERO
    sum_materials = agg['sum_materials'] or ZERO
    sum_machinery = agg['sum_machinery'] or ZERO
    sum_overhead = agg['sum_overhead'] or ZERO
    sum_total = agg['sum_total'] or ZERO

    coverage_pct = _safe_pct(Decimal(str(costed_count)), Decimal(str(total_count)))

    # Determine top category
    categories = {
        'labor': sum_labor,
        'materials': sum_materials,
        'machinery': sum_machinery,
        'overhead': sum_overhead,
    }
    top_category = max(categories, key=categories.get) if sum_total > ZERO else 'none'

    # Health status
    if coverage_pct >= Decimal("90"):
        health = "GREEN"
    elif coverage_pct >= Decimal("70"):
        health = "YELLOW"
    else:
        health = "RED"

    result = {
        "mode": mode,
        "total_activities": total_count,
        "costed_activities": costed_count,
        "costing_coverage_pct": str(coverage_pct),
        "cost_breakdown_pct": {
            "labor_pct": str(_safe_pct(sum_labor, sum_total)),
            "materials_pct": str(_safe_pct(sum_materials, sum_total)),
            "machinery_pct": str(_safe_pct(sum_machinery, sum_total)),
            "overhead_pct": str(_safe_pct(sum_overhead, sum_total)),
        },
        "top_expense_category": top_category,
        "shadow_health": health,
    }

    # [SHADOW ACCOUNTING DOCTRINE] In STRICT mode, also include absolute values
    if mode == FarmSettings.MODE_STRICT:
        result.update({
            "total_cost": str(sum_total.quantize(FOUR_DP)),
            "cost_labor": str(sum_labor.quantize(FOUR_DP)),
            "cost_materials": str(sum_materials.quantize(FOUR_DP)),
            "cost_machinery": str(sum_machinery.quantize(FOUR_DP)),
            "cost_overhead": str(sum_overhead.quantize(FOUR_DP)),
        })

    return Response(result)
