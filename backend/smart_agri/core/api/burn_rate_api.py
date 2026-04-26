"""
Burn Rate Summary API — لوحة معدل الحرق المصغّرة.

[AGRI-GUARDIAN Axis 8+15] Provides proportional completion rates (burn rate %)
to simple-mode users without leaking explicit absolute financial unit values.

Response: percentage-only data suitable for micro-dashboard display.
"""

import logging
from datetime import date as date_type
from decimal import Decimal

from django.db.models import Sum
from django.db import OperationalError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from smart_agri.core.api.error_contract import build_error_payload, request_id_from_request
from smart_agri.core.api.permissions import _ensure_user_has_farm_access

logger = logging.getLogger(__name__)

FOUR_DP = Decimal("0.0001")
ZERO = Decimal("0.0000")
HUNDRED = Decimal("100.0000")


def _pct(numerator, denominator):
    """Safe percentage calculation with Decimal."""
    if not denominator or denominator <= ZERO:
        return ZERO
    return ((numerator / denominator) * HUNDRED).quantize(FOUR_DP)  # agri-guardian: decimal-safe


def _status_from_pct(budget_pct: Decimal, elapsed_pct: Decimal) -> str:
    """
    Determine burn rate health status.
    - GREEN: budget usage is proportional to time elapsed (within 15% tolerance)
    - YELLOW: budget usage exceeds time by 15-30%
    - RED: budget usage exceeds time by >30% (critical burn)
    """
    if elapsed_pct <= ZERO:
        return 'GREEN'

    ratio = budget_pct / elapsed_pct if elapsed_pct > ZERO else ZERO  # agri-guardian: decimal-safe
    if ratio <= Decimal("1.15"):
        return 'GREEN'
    elif ratio <= Decimal("1.30"):
        return 'YELLOW'
    else:
        return 'RED'


def _compute_elapsed_pct(plan_dict: dict) -> Decimal:
    """
    [AGRI-GUARDIAN FIX] Compute real elapsed time percentage from CropPlan dates.

    Returns: Decimal between 0.0000 and 100.0000.
    Fallback: 50.0000 if dates are missing or invalid.
    """
    start = plan_dict.get('start_date')
    end = plan_dict.get('end_date')

    if not start or not end:
        return Decimal("50.0000")

    # Handle both date objects and strings
    if isinstance(start, str):
        try:
            start = date_type.fromisoformat(start)
        except ValueError:
            return Decimal("50.0000")
    if isinstance(end, str):
        try:
            end = date_type.fromisoformat(end)
        except ValueError:
            return Decimal("50.0000")

    total_days = (end - start).days
    if total_days <= 0:
        return Decimal("50.0000")

    elapsed_days = (date_type.today() - start).days
    elapsed_days = max(0, min(elapsed_days, total_days))

    pct = (Decimal(str(elapsed_days)) / Decimal(str(total_days))) * HUNDRED
    return pct.quantize(FOUR_DP)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def burn_rate_summary(request):
    """
    GET /api/v1/burn-rate-summary/?farm=<farm_id>

    Returns burn rate data for all active crop plans in the farm.
    **No absolute financial values** — only percentages and status indicators.

    Response format:
    [
        {
            "crop_plan_id": 1,
            "crop_plan_name": "قمح ربيعي 2026",
            "budget_pct_used": "45.2300",
            "elapsed_pct": "50.0000",
            "status": "GREEN",
            "labor_burn_pct": "40.0000",
            "material_burn_pct": "55.3000",
            "machinery_burn_pct": "30.0000"
        }
    ]
    """
    farm_id = request.query_params.get('farm')
    if not farm_id:
        return Response(
            build_error_payload(
                'معرّف المزرعة مطلوب (?farm=X).',
                request=request,
                code='FARM_REQUIRED',
            ),
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        farm_id = int(farm_id)
    except (ValueError, TypeError):
        return Response(
            build_error_payload(
                'معرّف المزرعة غير صالح.',
                request=request,
                code='INVALID_FARM_ID',
            ),
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        _ensure_user_has_farm_access(request.user, farm_id)
    except PermissionDenied as exc:
        return Response(
            build_error_payload(
                str(exc.detail),
                request=request,
                code='FARM_ACCESS_DENIED',
            ),
            status=status.HTTP_403_FORBIDDEN,
        )

    from smart_agri.core.models.planning import CropPlan
    from smart_agri.finance.models import FinancialLedger

    try:
        # Get active (non-settled) crop plans for this farm
        plans = CropPlan.objects.filter(
            farm_id=farm_id,
            deleted_at__isnull=True,
        ).exclude(
            status='SETTLED',
        ).values(
            'id', 'name', 'start_date', 'end_date',
            'budget_labor', 'budget_materials', 'budget_machinery',
        )

        results = []
        for plan in plans:
            plan_id = plan['id']
            budget_labor = plan.get('budget_labor') or ZERO
            budget_materials = plan.get('budget_materials') or ZERO
            budget_machinery = plan.get('budget_machinery') or ZERO
            total_budget = budget_labor + budget_materials + budget_machinery

            if total_budget <= ZERO:
                elapsed = _compute_elapsed_pct(plan)
                results.append({
                    'crop_plan_id': plan_id,
                    'crop_plan_name': plan.get('name', ''),
                    'budget_pct_used': '0.0000',
                    'elapsed_pct': str(elapsed),
                    'status': 'GREEN',
                    'labor_burn_pct': '0.0000',
                    'material_burn_pct': '0.0000',
                    'machinery_burn_pct': '0.0000',
                })
                continue

            # Sum actual costs from ledger (WIP debits for this crop plan)
            actuals = FinancialLedger.objects.filter(
                farm_id=farm_id,
                crop_plan_id=plan_id,
            ).aggregate(
                total_debit=Sum('debit'),
            )
            total_spent = actuals.get('total_debit') or ZERO

            # Calculate percentages (NO absolute values in response)
            budget_pct = _pct(total_spent, total_budget)

            # Elapsed % — computed from CropPlan start_date / end_date
            elapsed_pct = _compute_elapsed_pct(plan)

            burn_status = _status_from_pct(budget_pct, elapsed_pct)

            # Sub-category burns (labor, material, machinery)
            labor_burn = _pct(total_spent, budget_labor) if budget_labor > ZERO else ZERO
            material_burn = _pct(total_spent, budget_materials) if budget_materials > ZERO else ZERO
            machinery_burn = _pct(total_spent, budget_machinery) if budget_machinery > ZERO else ZERO

            results.append({
                'crop_plan_id': plan_id,
                'crop_plan_name': plan.get('name', ''),
                'budget_pct_used': str(budget_pct),
                'elapsed_pct': str(elapsed_pct),
                'status': burn_status,
                'labor_burn_pct': str(labor_burn),
                'material_burn_pct': str(material_burn),
                'machinery_burn_pct': str(machinery_burn),
            })

        return Response(results)
    except (ValidationError, TypeError, ValueError) as exc:
        logger.warning(
            "burn_rate_summary_validation_failed event=BURN_RATE_VALIDATION_FAIL farm_id=%s user_id=%s path=%s request_id=%s error=%s",
            farm_id,
            getattr(request.user, "id", None),
            getattr(request, "path", ""),
            request_id_from_request(request),
            exc,
        )
        return Response(
            build_error_payload(str(exc), request=request, code='BURN_RATE_VALIDATION_ERROR'),
            status=status.HTTP_400_BAD_REQUEST,
        )
    except (ImportError, OperationalError) as exc:
        logger.exception(
            "burn_rate_summary_runtime_failure event=BURN_RATE_RUNTIME_FAIL farm_id=%s user_id=%s path=%s request_id=%s",
            farm_id,
            getattr(request.user, "id", None),
            getattr(request, "path", ""),
            request_id_from_request(request),
        )
        return Response(
            build_error_payload(
                'حدث خطأ في حساب معدلات الحرق.',
                request=request,
                code='BURN_RATE_RUNTIME_ERROR',
            ),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
