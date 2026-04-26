"""
VarianceAnalysisService — تحليل انحراف السعر والكمية.

Provides deep variance analysis for crop plan costs:
  - Price Variance: (Standard Price - Actual WAC Price) × Actual Qty
  - Quantity Variance: (Standard BOM Qty - Actual Qty) × Standard Price
  - Total Variance = Price + Quantity

AGENTS.md Compliance:
  - Axis 5: Decimal(19,4)
  - Axis 6: Farm-scoped
  - Axis 8: Variance Controls
"""

import logging
from decimal import Decimal

from django.db.models import Sum, F, Value, CharField
from django.db.models.functions import Coalesce

logger = logging.getLogger(__name__)

FOUR_DP = Decimal("0.0001")
ZERO = Decimal("0.0000")


class VarianceAnalysisService:
    """
    [AGENTS.md] Deep variance analysis for crop plan vs actual.
    Calculates Price Variance and Quantity Variance per material.
    """

    @staticmethod
    def get_variance_report(*, farm_id, crop_plan_id=None, season_id=None):
        """
        Generate variance analysis report.

        Returns list of variance entries per material, grouped by crop plan.
        """
        from smart_agri.core.models.planning import CropPlan
        from smart_agri.core.models.crop import CropRecipeMaterial
        from smart_agri.core.models.activity import ActivityItem

        if not farm_id:
            return {"error": "[Axis 6] farm_id is required."}

        # Get crop plans
        plans_qs = CropPlan.objects.filter(
            farm_id=farm_id, deleted_at__isnull=True,
        )
        if crop_plan_id:
            plans_qs = plans_qs.filter(id=crop_plan_id)
        if season_id:
            plans_qs = plans_qs.filter(season_id=season_id)

        results = []

        for plan in plans_qs.select_related('crop', 'recipe'):
            plan_area = plan.area or Decimal("1")
            recipe = plan.recipe
            if not recipe:
                continue

            # Standard BOM materials for this recipe
            bom_materials = CropRecipeMaterial.objects.filter(
                recipe=recipe, deleted_at__isnull=True,
            ).select_related('item')

            plan_variances = []
            total_price_var = ZERO
            total_qty_var = ZERO

            for bom in bom_materials:
                item = bom.item
                std_qty_per_ha = bom.quantity_per_hectare or ZERO
                std_price = bom.unit_cost or ZERO
                standard_qty = (std_qty_per_ha * plan_area).quantize(FOUR_DP)
                standard_cost = (standard_qty * std_price).quantize(FOUR_DP)

                # Actual consumption from ActivityItems linked to this plan
                actuals = ActivityItem.objects.filter(
                    activity__crop_plan=plan,
                    item=item,
                    deleted_at__isnull=True,
                ).aggregate(
                    actual_qty=Coalesce(Sum('quantity'), ZERO),
                    actual_cost=Coalesce(Sum('total_cost'), ZERO),
                )
                actual_qty = actuals['actual_qty'].quantize(FOUR_DP) if actuals['actual_qty'] else ZERO
                actual_cost = actuals['actual_cost'].quantize(FOUR_DP) if actuals['actual_cost'] else ZERO

                # Actual unit price (WAC)
                actual_price = (actual_cost / actual_qty).quantize(FOUR_DP) if actual_qty > ZERO else ZERO  # agri-guardian: decimal-safe

                # Price Variance = (Std Price - Actual Price) × Actual Qty
                price_variance = ((std_price - actual_price) * actual_qty).quantize(FOUR_DP)

                # Quantity Variance = (Std Qty - Actual Qty) × Std Price
                qty_variance = ((standard_qty - actual_qty) * std_price).quantize(FOUR_DP)

                total_variance = (price_variance + qty_variance).quantize(FOUR_DP)

                total_price_var += price_variance
                total_qty_var += qty_variance

                plan_variances.append({
                    "item_id": item.id,
                    "item_name": item.name,
                    "standard_qty": str(standard_qty),
                    "standard_price": str(std_price),
                    "standard_cost": str(standard_cost),
                    "actual_qty": str(actual_qty),
                    "actual_price": str(actual_price),
                    "actual_cost": str(actual_cost),
                    "price_variance": str(price_variance),
                    "qty_variance": str(qty_variance),
                    "total_variance": str(total_variance),
                    "favorable": total_variance >= ZERO,
                })

            results.append({
                "crop_plan_id": plan.id,
                "crop_plan_name": plan.name,
                "crop": plan.crop.name if plan.crop else "",
                "area": str(plan_area),
                "total_price_variance": str(total_price_var),
                "total_qty_variance": str(total_qty_var),
                "total_variance": str((total_price_var + total_qty_var).quantize(FOUR_DP)),
                "materials": plan_variances,
            })

        return {
            "farm_id": farm_id,
            "plans_count": len(results),
            "plans": results,
        }
