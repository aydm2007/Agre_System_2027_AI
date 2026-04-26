from datetime import date
from decimal import Decimal
from django.db.models import Sum
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response

from smart_agri.core.models.planning import CropPlan, CropPlanBudgetLine
from smart_agri.core.models.activity import ActivityItem

class PredictiveVarianceViewSet(viewsets.ViewSet):
    """
    [YECO Shadow ERP] شاشة الانحرافات التنبؤية (Predictive Variance Dashboard).
    
    This endpoint calculates the run-rate (burn rate) of Active CropPlans 
    by comparing elapsed season time vs consumed materials.
    
    @idempotent (Read-Only)
    """
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        user = request.user
        active_plans = CropPlan.objects.filter(
            status='active',
            deleted_at__isnull=True
        ).select_related('farm', 'crop')

        # [AGRI-GUARDIAN] Tenant Isolation
        if not user.is_superuser:
            from smart_agri.core.api.permissions import user_farm_ids
            farm_ids = user_farm_ids(user)
            active_plans = active_plans.filter(farm_id__in=farm_ids)

        # [AGRI-GUARDIAN] URL Filters
        farm_filter = request.GET.get('farm')
        crop_plan_filter = request.GET.get('crop_plan')
        crop_filter = request.GET.get('crop')

        if farm_filter:
            active_plans = active_plans.filter(farm_id=farm_filter)
        if crop_plan_filter:
            active_plans = active_plans.filter(id=crop_plan_filter)
        if crop_filter:
            active_plans = active_plans.filter(crop_id=crop_filter)
        
        results = []
        today = date.today()

        for plan in active_plans:
            # 1. Calculate time factors
            if not plan.start_date or not plan.end_date or plan.start_date >= plan.end_date:
                continue
                
            total_days = (plan.end_date - plan.start_date).days
            elapsed_days = (today - plan.start_date).days
            
            if elapsed_days < 0:
                elapsed_days = 0 # Not started yet
            if elapsed_days > total_days:
                elapsed_days = total_days
                
            time_elapsed_ratio = Decimal(elapsed_days) / Decimal(total_days) if total_days > 0 else Decimal('0')
            
            # 2. Extract material budget
            # We focus on category = "materials"
            material_budgets = CropPlanBudgetLine.objects.filter(
                crop_plan=plan,
                category=CropPlanBudgetLine.CATEGORY_MATERIALS,
                deleted_at__isnull=True
            )
            total_material_budget = material_budgets.aggregate(total=Sum('total_budget'))['total'] or Decimal('0.0000')
            
            # 3. Aggregate actual material expenses
            actual_materials = ActivityItem.objects.filter(
                activity__crop_plan=plan,
                activity__log__log_date__gte=plan.start_date,
                activity__log__log_date__lte=today,
                activity__deleted_at__isnull=True,
                deleted_at__isnull=True,
            )
            
            actual_material_cost = Decimal('0.0000')
            for usage in actual_materials:
                # [AGRI-GUARDIAN] Strict Accounting: Use frozen historical cost_per_unit 
                # (to prevent historical variances when global item prices change)
                if usage.cost_per_unit and usage.cost_per_unit > 0:
                    actual_material_cost += (usage.qty * usage.cost_per_unit)
                elif usage.item and usage.item.unit_price:
                    # Fallback for legacy records that missed the snapshot
                    actual_material_cost += (usage.qty * usage.item.unit_price)

            # 4. Extrapolate projected run-rate
            projected_total_cost = Decimal('0.0000')
            if elapsed_days > 0:
                daily_burn_rate = actual_material_cost / Decimal(elapsed_days)
                projected_total_cost = daily_burn_rate * Decimal(total_days)
            
            # 5. Determine warning thresholds
            variance_ratio = Decimal('0.0000')
            if total_material_budget > 0:
                variance_ratio = (projected_total_cost / total_material_budget) * Decimal('100.00')

            health_status = 'GREEN'
            if variance_ratio > Decimal('100'):
                health_status = 'CRITICAL'
            elif variance_ratio > Decimal('85'):
                health_status = 'WARNING'
                
            results.append({
                "plan_id": plan.id,
                "plan_name": plan.name,
                "farm_name": plan.farm.name,
                "crop_name": plan.crop.name,
                "total_days": total_days,
                "elapsed_days": elapsed_days,
                "time_elapsed_ratio": str((time_elapsed_ratio * Decimal('100.0')).quantize(Decimal('0.01'))),
                
                # [AGRI-GUARDIAN §Axis-5] Use str() for Decimal serialization, never float()
                "total_material_budget": str(total_material_budget),
                "actual_material_cost": str(actual_material_cost),
                "projected_total_cost": str(projected_total_cost),
                
                "variance_ratio": str(variance_ratio),
                "health_status": health_status
            })

        return Response({
            "status": "success",
            "count": len(results),
            "results": results
        }, status=status.HTTP_200_OK)
