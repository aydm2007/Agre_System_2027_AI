from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import models


def calculate_identityless_casual_cost(activity: Any) -> None:
    """
    Fallback costing path for casual batch rows without employee identities.
    Preserves doctrine: costing is based on persisted wage_cost, not HR identity.
    """
    from smart_agri.core.models.activity import ActivityCostSnapshot

    labor_cost = (
        activity.employee_details.filter(labor_type='CASUAL_BATCH')
        .aggregate(total=models.Sum('wage_cost'))
        .get('total')
        or Decimal('0.0000')
    )

    material_cost = Decimal('0.0000')
    for item_usage in activity.items.all().select_related('item'):
        unit_price = item_usage.item.unit_price or Decimal('0')
        line_cost = (item_usage.qty or Decimal('0')) * unit_price
        if item_usage.total_cost != line_cost:
            item_usage.cost_per_unit = unit_price
            item_usage.total_cost = line_cost
            item_usage.save(update_fields=['cost_per_unit', 'total_cost'])
        material_cost += line_cost

    machinery_cost = Decimal('0.0000')
    if hasattr(activity, 'machine_details'):
        usage = activity.machine_details
        hours = usage.machine_hours or Decimal('0')
        asset = activity.asset
        if asset:
            rate = asset.operational_cost_per_hour or Decimal('0')
            machinery_cost += hours * rate

    overhead_cost = Decimal('0.0000')
    total_cost = labor_cost + material_cost + machinery_cost + overhead_cost

    activity.cost_labor = labor_cost
    activity.cost_materials = material_cost
    activity.cost_machinery = machinery_cost
    activity.cost_overhead = overhead_cost
    activity.cost_total = total_cost
    activity.save(
        update_fields=['cost_labor', 'cost_materials', 'cost_machinery', 'cost_overhead', 'cost_total']
    )

    ActivityCostSnapshot.objects.create(
        activity=activity,
        crop_plan=activity.crop_plan,
        task=activity.task,
        cost_labor=labor_cost,
        cost_materials=material_cost,
        cost_machinery=machinery_cost,
        cost_overhead=overhead_cost,
        cost_total=total_cost,
        currency='YER',
    )
