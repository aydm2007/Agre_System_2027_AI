from decimal import Decimal
import logging
from django.conf import settings
from django.db import transaction
from django.db.models import Sum, Q
from django.db.models.functions import Coalesce
from django.utils import timezone
from smart_agri.core.models.farm import Farm
from smart_agri.core.models.planning import CropPlan, CropPlanBudgetLine
from smart_agri.core.models.activity import Activity
from smart_agri.core.models.settings import Supervisor, LaborRate, MachineRate
from smart_agri.finance.models import FinancialLedger, CostConfiguration
from smart_agri.core.constants import CropPlanStatus

logger = logging.getLogger(__name__)

class CostAllocationService:
    """
    Commercial Logic Layer: Allocates overheads and indirect costs.
    Ensures that 'Blind Costing' is eliminated by distributing fixed costs
    (Managers, Security, Electricity) to productive units (Crops/Fields).
    """

    @staticmethod
    def _to_m2(area_value, uom):
        """Convert area to m² using Yemeni-relevant units."""
        area = Decimal(str(area_value or 0))
        unit = (uom or "").strip().lower()
        if unit in {"ha", "hectare", "hectares"}:
            return area * Decimal("10000")
        if unit in {"dunum", "dunums"}:
            return area * Decimal("1000")
        if unit in {"libnah"}:
            # اللبنة اليمنية ≈ 44.4 م² (تقريب شائع في المناطق الزراعية)
            return area * Decimal("44.4")
        return area

    @staticmethod
    def _compute_plan_area_m2(plan: CropPlan, period_start, period_end) -> Decimal:
        activities = (
            Activity.objects.filter(
                crop_plan=plan,
                deleted_at__isnull=True,
                log__log_date__range=(period_start, period_end),
            )
            .select_related("task")
            .prefetch_related("planting_details")
        )
        total = Decimal("0")
        for activity in activities:
            if activity.task and not getattr(activity.task, "requires_area", False):
                continue
            ext = getattr(activity, "planting_details", None)
            if ext is not None:
                if getattr(ext, "planted_area_m2", None):
                    total += Decimal(str(ext.planted_area_m2))
                    continue
                total += CostAllocationService._to_m2(
                    getattr(ext, "planted_area", 0),
                    getattr(ext, "planted_uom", "m2"),
                )
                continue
            payload = activity.data if isinstance(activity.data, dict) else {}
            if payload.get("planted_area") is not None:
                total += CostAllocationService._to_m2(
                    payload.get("planted_area"),
                    payload.get("planted_uom", "m2"),
                )
        return total

    @staticmethod
    def allocate_overheads_by_area(farm: Farm, period_start, period_end, user=None):
        """
        Distributes farm-level overheads based on planted area (Hectares) of active plans.
        """
        # 1. Fetch Total Overhead Pool for Period (e.g. from General Ledger or Config)
        # For MVP: We use the 'Overhead Rate' from CostConfiguration * Total Farm Area
        # Ideally, this should come from actual bills, but we start with Standard Costing.
        
        try:
            config = CostConfiguration.objects.get(farm=farm, deleted_at__isnull=True)
            if not config.overhead_rate_per_hectare:
                from django.core.exceptions import ValidationError
                raise ValidationError(
                    f"معدل التكاليف غير المباشرة غير محدد للمزرعة {farm.name}. "
                    f"يجب تحديث إعدادات التكاليف في CostConfiguration."
                )
            
            rate_per_ha = config.overhead_rate_per_hectare
        except CostConfiguration.DoesNotExist:
            # AGRI-GUARDIAN: Financial Integrity - Always raise, never default to 0
            from django.core.exceptions import ValidationError
            raise ValidationError(
                f"إعدادات التكاليف مفقودة للمزرعة {farm.name}. "
                f"يجب تحديد 'معدل التكاليف غير المباشرة لكل هكتار' في CostConfiguration."
            )

        active_plans = CropPlan.objects.filter(
            farm=farm,
            status=CropPlanStatus.ACTIVE,
            start_date__lte=period_end,
            end_date__gte=period_start
        )

        if not active_plans.exists():
            return Decimal("0")

        total_allocated = Decimal("0")
        HECTARE_M2 = Decimal("10000")

        # 3. Distribute — [AGRI-GUARDIAN] Individual create() ensures save()/clean()
        # runs fiscal period check, row_hash computation, and AuditLog entry.
        with transaction.atomic():
            for plan in active_plans:
                planted_area = CostAllocationService._compute_plan_area_m2(
                    plan, period_start, period_end
                )
                
                from decimal import getcontext
                area_ha = getcontext().divide(planted_area, getattr(HECTARE_M2, "value", HECTARE_M2)).quantize(Decimal("0.000001"))
                
                if area_ha > 0:
                    allocation_amount = area_ha * rate_per_ha
                    description = f"تخصيص تكاليف غير مباشرة: {period_start} إلى {period_end} ({area_ha:.2f} هكتار)"
                    common_kwargs = dict(
                        crop_plan=plan,
                        cost_center=getattr(plan, 'cost_center', None),
                        description=description,
                        currency=plan.currency or getattr(settings, 'DEFAULT_CURRENCY', 'YER'),
                        farm=farm,
                        created_by=user,
                    )

                    # [AGRI-GUARDIAN] Double-Entry: Debit Overhead Expense
                    FinancialLedger.objects.create(
                        account_code=FinancialLedger.ACCOUNT_OVERHEAD,
                        debit=allocation_amount,
                        credit=Decimal("0"),
                        **common_kwargs,
                    )
                    # [AGRI-GUARDIAN] Double-Entry: Credit Liability (Sector Payable)
                    FinancialLedger.objects.create(
                        account_code=FinancialLedger.ACCOUNT_SECTOR_PAYABLE,
                        debit=Decimal("0"),
                        credit=allocation_amount,
                        **common_kwargs,
                    )
                    total_allocated += allocation_amount

        return total_allocated

    @staticmethod
    def allocate_actual_bills(farm: Farm, period_start, period_end):
        """
        Distributes ACTUAL bills (Electricity, Rent) to active crops based on area.
        Replaces 'Blind Estimates' with 'Financial Reality'.
        """
        from smart_agri.finance.models import ActualExpense, FinancialLedger
        
        # 1. Find Unallocated Bills for this period
        expenses = ActualExpense.objects.filter(
            farm=farm,
            is_allocated=False,
            period_start__gte=period_start, # Overlap logic simplified for now
            period_end__lte=period_end
        )
        
        if not expenses.exists():
            return Decimal("0")

        # 2. Find Activity Drivers (Area)
        # 2. Find Activity Drivers (Area) - Optimized (No N+1)
        active_plans = CropPlan.objects.filter(
            farm=farm,
            status=CropPlanStatus.ACTIVE,
            start_date__lte=period_end,
            end_date__gte=period_start
        )
        
        # Calculate Total Driver (Total Planted Area)
        plan_areas = {}
        total_farm_area = Decimal("0")
        
        for plan in active_plans:
             planted = CostAllocationService._compute_plan_area_m2(
                 plan, period_start, period_end
             )
             if not planted or planted <= 0:
                 # Fallback to planned area (hectares) when no activity-level planted area exists.
                 planned_ha = Decimal(str(getattr(plan, "area", 0) or 0))
                 planted = planned_ha * Decimal("10000")
             
             if planted > 0:
                 plan_areas[plan.id] = planted
                 total_farm_area += planted
        
        if total_farm_area == 0:
            logger.warning("No planted area found to allocate actual expenses.")
            return Decimal("0")

        total_distributed = Decimal("0")

        # [Agri-Guardian] Financial Precision Constants
        ALLOCATION_PRECISION = Decimal("0.000001") # High precision for internal weights
        CURRENCY_PRECISION = Decimal("0.01")       # YER standard (Fils/Cents)

        with transaction.atomic():
            for expense in expenses:
                remaining_amount = expense.amount
                
                # Sort plans to ensure deterministic distribution (Auditability)
                sorted_plans = sorted(active_plans, key=lambda p: p.id)
                
                for i, plan in enumerate(sorted_plans):
                    plan_area = plan_areas.get(plan.id, Decimal("0"))
                    if plan_area == 0:
                        continue
                    
                    # Last item gets the remainder to ensure Sum(parts) == Total exactly
                    is_last = (i == len(sorted_plans) - 1)
                    
                    if is_last:
                        share = remaining_amount
                    else:
                        from decimal import getcontext
                        weight = getcontext().divide(plan_area, getattr(total_farm_area, "value", total_farm_area)).quantize(ALLOCATION_PRECISION)
                        share = (expense.amount * weight).quantize(CURRENCY_PRECISION)
                    
                    # Integrity Check: Don't allocate negative remainder due to rounding anomalies
                    if share < 0: share = Decimal("0")
                    if share > remaining_amount: share = remaining_amount

                    remaining_amount -= share

                    FinancialLedger.objects.create(
                        crop_plan=plan,
                        cost_center=getattr(plan, 'cost_center', None),
                        account_code=expense.account_code,
                        debit=share,
                        credit=0,
                        description=f"تخصيص مصروف فعلي: {expense.description}",
                        created_by=expense.farm.supervisors.first().user if expense.farm.supervisors.exists() else None, 
                        currency=getattr(settings, 'DEFAULT_CURRENCY', 'YER'),
                        farm=farm
                    )
                    total_distributed += share
                
                # Mark as Allocated
                expense.is_allocated = True
                expense.allocated_at = timezone.now()
                expense.save()
                
        return total_distributed
