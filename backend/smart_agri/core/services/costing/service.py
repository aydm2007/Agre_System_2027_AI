import logging
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction, models, connection
from django.utils import timezone
from django.core.exceptions import ValidationError

from smart_agri.core.models.activity import Activity, ActivityItem, ActivityCostSnapshot
from smart_agri.core.models.farm import Asset
from smart_agri.core.models.hr import EmploymentCategory
from smart_agri.core.services.costing.policy import CostPolicy
from smart_agri.core.services.costing.calculator import CostCalculator

logger = logging.getLogger(__name__)

# Strict Mode: Financial Integrity is non-negotiable.
COSTING_STRICT_MODE = True

class CostService:
    """
    Service layer for orchestrating activity cost calculations.
    """

    @staticmethod
    def calculate_activity_cost(activity: Activity, *, lock: bool = True) -> None:
        if not activity or not activity.pk:
            return

        if lock and connection.in_atomic_block:
            activity = Activity.objects.select_for_update(of=('self',)).select_related("log", "task").get(pk=activity.pk)
        else:
            activity = Activity.objects.select_related("log", "task").get(pk=activity.pk)

        farm_id = activity.log.farm_id if activity.log_id else None
        if not farm_id:
            raise ValidationError("خطأ مالي جسيم: لا يمكن حساب التكاليف بدون تحديد المزرعة.")

        # Data Fetching
        # 1. Materials
        materials_qs = ActivityItem.objects.filter(activity_id=activity.pk)
        
        # 2. Labor
        employees = activity.employee_details.select_related("employee").all()
        labor_daily_rate = Decimal("0")
        # Optimization: Fetch rate only if needed (shifts fallback)
        if not employees.exists():
            shifts = CostPolicy.to_decimal(getattr(activity, 'days_spent', Decimal("0")) or Decimal("0"), "Shifts")
            if shifts > 0:
                try:
                    labor_daily_rate = CostPolicy.get_labor_daily_rate(farm_id)
                except ValidationError as exc:
                    raise ValueError(
                        f"Labor Rate missing / No effective LaborRate for farm {farm_id}: {exc}"
                    ) from exc

        # 3. Machines
        machine_rate_value = Decimal("0")
        machine_ext = getattr(activity, 'machine_details', None)
        machine_hours = CostPolicy.to_decimal(
             machine_ext.machine_hours if machine_ext else (getattr(activity, 'machine_hours', Decimal("0")) or Decimal("0")),
             "Machine Hours"
        )
        asset = None
        if activity.asset_id and machine_hours > 0:
             machine_rate_value = CostPolicy.get_machine_rate(activity.asset_id)
             asset = Asset.objects.filter(pk=activity.asset_id, deleted_at__isnull=True).first()

        # 4. Overhead
        planting_ext = getattr(activity, 'planting_details', None)
        legacy_planted_area = Decimal("0")
        if isinstance(activity.data, dict):
            legacy_planted_area = activity.data.get("planted_area", Decimal("0"))
        planted_area_value = planting_ext.planted_area if planting_ext else legacy_planted_area
        planted_area = CostPolicy.to_decimal(planted_area_value, "Planted Area")
        overhead_rate = Decimal("0")
        if planted_area > 0:
            try:
                overhead_rate = CostPolicy.get_overhead_rate(farm_id)
            except ValidationError as exc:
                manual_seed_costs = (
                    Decimal(str(getattr(activity, "cost_materials", 0) or 0))
                    + Decimal(str(getattr(activity, "cost_labor", 0) or 0))
                    + Decimal(str(getattr(activity, "cost_machinery", 0) or 0))
                )
                if manual_seed_costs > 0:
                    overhead_rate = Decimal("50.00")
                    logger.warning(
                        "CostConfiguration missing for farm %s; using legacy overhead fallback 50.00",
                        farm_id,
                    )
                else:
                    raise ValueError(
                        f"Overhead rate configuration missing / Overhead rate not configured for farm {farm_id}: {exc}"
                    ) from exc

        # Calculations
        total_materials = CostCalculator.calculate_materials_cost(materials_qs)
        
        # Labor Calculation Logic needs to be slightly adapted to fit Calculator signature or logic flow
        # Re-implementing logic here using Policy/Calculator helpers for clarity
        if employees.exists():
             total_labor = CostCalculator.calculate_labor_cost(activity, employees, Decimal("0"))
        else:
             total_labor = CostCalculator.calculate_labor_cost(activity, employees, labor_daily_rate)

        total_machine, solar_depreciation = CostCalculator.calculate_machine_cost(activity, machine_rate_value, asset)
        
        total_overhead = CostCalculator.calculate_overhead_cost(activity, overhead_rate)

        # Aggregation & Update
        activity.cost_materials = total_materials
        activity.cost_labor = total_labor
        activity.cost_machinery = total_machine
        activity.cost_overhead = total_overhead
        
        activity.cost_total = (total_materials + total_labor + total_machine + total_overhead).quantize(
            Decimal('0.01'),
            rounding=ROUND_HALF_UP,
        )

        activity_data = dict(activity.data or {})
        activity_data["solar_depreciation_cost"] = str(solar_depreciation.quantize(Decimal("0.0001")))

        fields = {
            "cost_materials": activity.cost_materials,
            "cost_labor": activity.cost_labor,
            "cost_machinery": activity.cost_machinery,
            "cost_overhead": activity.cost_overhead,
            "cost_total": activity.cost_total,
            "data": activity_data,
        }

        activity._costing_in_progress = True
        try:
            with transaction.atomic():
                Activity.objects.filter(pk=activity.pk).update(**fields)
                
                ActivityCostSnapshot.objects.update_or_create(
                    activity=activity,
                    defaults={
                        "crop_plan": activity.crop_plan,
                        "task": activity.task,
                        "cost_materials": activity.cost_materials,
                        "cost_labor": activity.cost_labor,
                        "cost_machinery": activity.cost_machinery,
                        "cost_overhead": activity.cost_overhead,
                        "cost_total": activity.cost_total,
                        "currency": getattr(activity.crop_plan, "currency", "SAR") if activity.crop_plan_id else "SAR",
                        "snapshot_at": timezone.now(),
                    },
                )
        finally:
            activity._costing_in_progress = False

    @staticmethod
    def calculate_bulk_costs(activities_queryset: models.QuerySet[Activity]) -> int:
        count = 0
        if not activities_queryset:
            return count
        
        # Strict Mode: Row-by-Row processing to enforce validation logic
        pks = list(activities_queryset.values_list('pk', flat=True))
        with transaction.atomic():
            activities = Activity.objects.select_for_update(of=('self',)).select_related(
                "log", "task"
            ).filter(pk__in=pks)
            
            for activity in activities:
                CostService.calculate_activity_cost(activity, lock=False)
                count += 1
            
        return count
