"""
Support helpers for the financial ledger API.

This module isolates query shaping, farm resolution, idempotency coordination,
and material variance calculations so api_ledger.py stays orchestration-focused.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from django.db.models import Count, DecimalField, Q, QuerySet, Sum
from rest_framework import status
from rest_framework.response import Response

from smart_agri.core.api.permissions import _ensure_user_has_farm_access, user_farm_ids
from smart_agri.finance.models import FinancialLedger

QUANTIZED_FOUR_DP = Decimal('0.0000')


@dataclass(frozen=True)
class FarmActionContext:
    farm: Any
    key: str | None


def build_ledger_queryset_for_user(*, request, user) -> QuerySet:
    qs = FinancialLedger.objects.select_related(
        'activity', 'created_by', 'approved_by', 'farm', 'crop_plan', 'cost_center'
    ).order_by('-created_at')

    if not user.is_superuser:
        allowed_farms = user_farm_ids(user)
        qs = qs.filter(
            Q(farm_id__in=allowed_farms)
            | Q(activity__crop_plan__farm_id__in=allowed_farms)
            | Q(activity__log__farm_id__in=allowed_farms)
        ).distinct()

    farm_param = request.query_params.get('farm') or request.query_params.get('farm_id')
    if farm_param:
        qs = qs.filter(
            Q(farm_id=farm_param)
            | Q(activity__crop_plan__farm_id=farm_param)
            | Q(activity__log__farm_id=farm_param)
        ).distinct()

    return qs


def summarize_ledger_queryset(qs: QuerySet) -> dict[str, Any]:
    totals = qs.aggregate(
        total_debit=Sum('debit', output_field=DecimalField()),
        total_credit=Sum('credit', output_field=DecimalField()),
        entry_count=Count('id'),
    )
    total_debit = totals['total_debit'] or Decimal('0')
    total_credit = totals['total_credit'] or Decimal('0')
    by_account = list(
        qs.values('account_code').annotate(
            debit=Sum('debit', output_field=DecimalField()),
            credit=Sum('credit', output_field=DecimalField()),
        ).order_by('account_code')
    )
    return {
        'totals': {
            'debit': total_debit,
            'credit': total_credit,
            'balance': total_debit - total_credit,
            'entry_count': totals['entry_count'] or 0,
        },
        'by_account': by_account,
    }


def analytical_summary_for_queryset(qs: QuerySet) -> dict[str, list[dict[str, Any]]]:
    by_cost_center = list(
        qs.values('cost_center__id', 'cost_center__name').annotate(
            debit=Sum('debit', output_field=DecimalField()),
            credit=Sum('credit', output_field=DecimalField()),
        ).order_by('cost_center__name')
    )
    by_crop_plan = list(
        qs.values('crop_plan__id', 'crop_plan__name').annotate(
            debit=Sum('debit', output_field=DecimalField()),
            credit=Sum('credit', output_field=DecimalField()),
        ).order_by('crop_plan__name')
    )
    return {'by_cost_center': by_cost_center, 'by_crop_plan': by_crop_plan}


def resolve_farm_action_context(*, request, viewset, farm_id) -> FarmActionContext | Response:
    from smart_agri.core.models.farm import Farm

    if not farm_id:
        return Response({'error': 'farm_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        farm = Farm.objects.get(id=farm_id)
    except Farm.DoesNotExist:
        return Response({'error': 'Farm not found.'}, status=status.HTTP_404_NOT_FOUND)

    _ensure_user_has_farm_access(request.user, farm.id)
    key, error_response = viewset._enforce_action_idempotency(request, farm.id)
    if error_response:
        return error_response
    return FarmActionContext(farm=farm, key=key)


def ensure_crop_plan_access(*, request, crop_plan_id):
    from smart_agri.core.models.planning import CropPlan

    if not crop_plan_id:
        return None, Response({'error': 'crop_plan_id parameter is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        crop_plan = CropPlan.objects.get(id=crop_plan_id)
    except CropPlan.DoesNotExist:
        return None, Response({'error': 'Crop Plan not found.'}, status=status.HTTP_404_NOT_FOUND)

    _ensure_user_has_farm_access(request.user, crop_plan.farm_id)
    return crop_plan, None


def build_standard_bom(crop_plan) -> dict[int, dict[str, Any]]:
    std_bom: dict[int, dict[str, Any]] = {}
    materials_source = None
    if getattr(crop_plan, 'recipe', None):
        materials_source = crop_plan.recipe.materials.all()
    elif getattr(crop_plan, 'template', None):
        materials_source = crop_plan.template.materials.all()

    if not materials_source:
        return std_bom

    for material in materials_source:
        std_cost = material.cost_override or (material.item.base_cost if material.item else 0)
        std_bom[material.item_id] = {
            'item_name': material.item.name,
            'std_qty': material.qty or Decimal('0'),
            'std_cost_per_unit': std_cost or Decimal('0'),
            'actual_qty': Decimal('0'),
            'actual_cost': Decimal('0'),
        }
    return std_bom


def accumulate_actual_materials(*, crop_plan, std_bom: dict[int, dict[str, Any]]) -> dict[int, dict[str, Any]]:
    from smart_agri.core.models.activity import Activity, ActivityItem

    activities = Activity.objects.filter(crop_plan=crop_plan, deleted_at__isnull=True)
    for activity in activities:
        for act_item in ActivityItem.objects.filter(activity=activity):
            item_id = act_item.item_id
            if not item_id:
                continue
            if item_id not in std_bom:
                std_bom[item_id] = {
                    'item_name': act_item.item.name if act_item.item else 'Unknown',
                    'std_qty': Decimal('0'),
                    'std_cost_per_unit': Decimal('0'),
                    'actual_qty': Decimal('0'),
                    'actual_cost': Decimal('0'),
                }
            qty = Decimal(str(act_item.qty)) if act_item.qty else Decimal('0')
            std_bom[item_id]['actual_qty'] += qty
            unit_cost = Decimal(str(act_item.item.base_cost)) if (act_item.item and act_item.item.base_cost) else Decimal('0')
            std_bom[item_id]['actual_cost'] += qty * unit_cost
    return std_bom


def compute_material_variance_report(std_bom: dict[int, dict[str, Any]]) -> dict[str, Any]:
    variance_report = []
    total_qty_variance = Decimal('0')
    total_price_variance = Decimal('0')

    for item_id, data in std_bom.items():
        sq = data['std_qty']
        sp = data['std_cost_per_unit']
        aq = data['actual_qty']
        ac = data['actual_cost']
        ap = (ac / aq).quantize(QUANTIZED_FOUR_DP) if aq > 0 else Decimal('0')  # agri-guardian: decimal-safe
        qty_var = (sq - aq) * sp
        price_var = (sp - ap) * aq
        total_qty_variance += qty_var
        total_price_variance += price_var
        variance_report.append({
            'item_id': item_id,
            'item_name': data['item_name'],
            'standard_qty': str(sq),
            'actual_qty': str(aq),
            'standard_cost_per_unit': str(sp),
            'actual_cost_per_unit': str(ap),
            'quantity_variance': str(qty_var.quantize(QUANTIZED_FOUR_DP)),
            'price_variance': str(price_var.quantize(QUANTIZED_FOUR_DP)),
            'total_variance': str((qty_var + price_var).quantize(QUANTIZED_FOUR_DP)),
        })

    return {
        'overall_summary': {
            'total_quantity_variance': str(total_qty_variance.quantize(QUANTIZED_FOUR_DP)),
            'total_price_variance': str(total_price_variance.quantize(QUANTIZED_FOUR_DP)),
            'net_variance': str((total_qty_variance + total_price_variance).quantize(QUANTIZED_FOUR_DP)),
        },
        'detailed_materials': variance_report,
    }
