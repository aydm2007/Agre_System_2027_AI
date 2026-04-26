from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.utils import timezone
from smart_agri.core.models import Activity, ActivityCostSnapshot
from smart_agri.finance.models import CostConfiguration, FinancialLedger

class CostingService:
    """
    [AGRI-GUARDIAN] Costing Engine
    Calculates the financial impact of Activities based on:
    1. Labor (Surrah System)
    2. Materials (Inventory Cost)
    3. Machinery (Operational Rate)
    4. Overheads (Per Hectare/Unit)

    [SHADOW ACCOUNTING DOCTRINE — PRD V21 §7.2, AGENTS.md Axis 4]
    This service computes costs in BOTH SIMPLE and STRICT modes for reporting
    transparency. However, any resulting FinancialLedger entries (depreciation,
    cost allocation) are only posted when the farm is in STRICT mode.
    In SIMPLE mode, cost_total/cost_labor/etc on Activity are "shadow" values
    for operational awareness — they do NOT flow to FinancialLedger or Treasury.
    The boundary is enforced by `enforce_strict_mode()` at the service layer
    (PettyCash, SupplierSettlement, Treasury) and `StrictModeRequired` at the
    API layer (all financial ViewSets).
    """

    @staticmethod
    def _resolve_currency(activity: Activity) -> str:
        default_currency = getattr(settings, "DEFAULT_CURRENCY", "YER")
        crop_plan = getattr(activity, "crop_plan", None)
        plan_currency = getattr(crop_plan, "currency", None)
        if plan_currency:
            return plan_currency

        farm = None
        if getattr(activity, "log_id", None) and getattr(activity.log, "farm_id", None):
            farm = activity.log.farm
        elif crop_plan and getattr(crop_plan, "farm_id", None):
            farm = crop_plan.farm

        farm_settings = getattr(farm, "settings", None) if farm else None
        farm_currency = getattr(farm_settings, "currency", None)
        return farm_currency or default_currency

    @staticmethod
    @transaction.atomic
    def calculate_activity_cost(activity: Activity) -> ActivityCostSnapshot:
        """
        Calculates and freezes the cost of an activity into a Snapshot.
        Updates the Activity's cached cost fields.
        """
        
        # 1. Labor Cost
        labor_cost = Decimal("0.0000")
        from smart_agri.core.services.costing.policy import CostPolicy
        
        # Ensure we fetch related employees
        for emp_detail in activity.employee_details.all().select_related('employee'):
            # [Omega-2028] DUAL-MODE Labor Costing Logic
            if emp_detail.is_hourly:
                # Direct Hourly Calculation: Workers * Hours * Rate
                # For registered employees, workers_count is 0 in the model but treated as 1 for math
                multiplier = emp_detail.workers_count if (emp_detail.workers_count or 0) > 0 else Decimal("1.00")
                line_cost = (multiplier * (emp_detail.hours_worked or 0) * (emp_detail.hourly_rate or 0))
            else:
                # Traditional Surrah-based Calculation
                if emp_detail.employee:
                    rate = emp_detail.employee.shift_rate or Decimal("0")
                else:
                    # CASUAL_BATCH with identityless labor: use farm default daily rate
                    rate = CostPolicy.get_labor_daily_rate(activity.log.farm_id)
                
                share = emp_detail.surrah_share or Decimal("0")
                line_cost = rate * share
            
            line_cost = line_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            
            # Update the line item cache
            if emp_detail.wage_cost != line_cost:
                emp_detail.wage_cost = line_cost
                emp_detail.save(update_fields=['wage_cost'])
            
            labor_cost += line_cost

        # 2. Material Cost
        # Sum of ActivityItem costs
        material_cost = Decimal("0.0000")
        wastage_cost = Decimal("0.0000")
        for item_usage in activity.items.all().select_related('item'):
            # Price Strategy: Dynamic Weighted Average Cost (WAC)
            # WAC is continuously updated in InventoryService._update_moving_average_cost during GRNs.
            unit_price = item_usage.item.unit_price or Decimal("0")
            applied_qty = item_usage.applied_qty if item_usage.applied_qty is not None else (item_usage.qty or Decimal("0"))
            waste_qty = item_usage.waste_qty or Decimal("0")
            line_cost = applied_qty * unit_price
            total_line_cost = (applied_qty + waste_qty) * unit_price
            
            if item_usage.total_cost != total_line_cost:
                item_usage.cost_per_unit = unit_price
                item_usage.total_cost = total_line_cost
                item_usage.save(update_fields=['cost_per_unit', 'total_cost'])
                
            material_cost += line_cost
            wastage_cost += waste_qty * unit_price

        # 3. Machinery Cost (Depreciation/Operational Rate)
        machinery_cost = Decimal("0.0000")
        # Check explicit machine usage details
        if hasattr(activity, 'machine_details'):
            usage = activity.machine_details
            hours = usage.machine_hours or Decimal("0")
            # If asset is linked to activity
            asset = activity.asset
            if asset:
                # [AGRI-GUARDIAN] Respect Farm Governance for Depreciation
                # Only calculate if enable_depreciation is True in FarmSettings.
                farm = activity.log.farm if activity.log else (activity.crop_plan.farm if activity.crop_plan else None)
                try:
                    is_depreciation_enabled = farm.settings.enable_depreciation if farm else False
                except (AttributeError, LookupError, ObjectDoesNotExist):
                    is_depreciation_enabled = False # Default strict/safe

                if is_depreciation_enabled:
                    rate = asset.operational_cost_per_hour or Decimal("0")
                    machinery_cost += hours * rate
                    
                    # [AGRI-GUARDIAN] Zero-Book Value Guard (IAS 16)
                    from django.db.models import Sum
                    total_depreciation = FinancialLedger.objects.filter(
                        farm=farm,
                        account_code=FinancialLedger.ACCOUNT_ACCUM_DEPRECIATION,
                        description__icontains=f"إهلاك آلة {asset.name}"
                    ).aggregate(total=Sum('credit'))['total'] or Decimal("0")
                    
                    remaining_value = asset.purchase_value - total_depreciation
                    if remaining_value < machinery_cost:
                        machinery_cost = max(Decimal("0"), remaining_value)
                    
                    # [AGRI-GUARDIAN] IAS-16 Automated Ledger Entry 
                    if machinery_cost > 0:
                        # [AGRI-GUARDIAN] Append-Only Compliance:
                        # Instead of deleting previous entries, create REVERSAL entries
                        # to maintain full audit trail (IAS-16 best practice).
                        previous_entries = FinancialLedger.objects.filter(
                            activity=activity,
                            account_code__in=[FinancialLedger.ACCOUNT_DEPRECIATION_EXPENSE, FinancialLedger.ACCOUNT_ACCUM_DEPRECIATION],
                            description__startswith=f"إهلاك آلة {asset.name}",
                        )
                        if previous_entries.exists():
                            for prev in previous_entries:
                                FinancialLedger.objects.create(
                                    activity=activity,
                                    farm=farm,
                                    account_code=prev.account_code,
                                    debit=-prev.debit if prev.debit else Decimal("0"),
                                    credit=-prev.credit if prev.credit else Decimal("0"),
                                    description=f"[عكس] {prev.description}",
                                    currency=prev.currency,
                                    idempotency_key=f"REV_{prev.idempotency_key}_{timezone.now().timestamp()}"
                                )
                        
                        currency = CostingService._resolve_currency(activity)
                        
                        # Debit: Depreciation Expense
                        FinancialLedger.objects.create(
                            activity=activity,
                            farm=farm,
                            account_code=FinancialLedger.ACCOUNT_DEPRECIATION_EXPENSE,
                            debit=machinery_cost,
                            credit=Decimal("0"),
                            description=f"إهلاك آلة {asset.name} إجباري بناءً على {hours} ساعة عمل",
                            currency=currency,
                            idempotency_key=f"DEP_EXP_{activity.id}_{timezone.now().timestamp()}"
                        )
                        # Credit: Accumulated Depreciation 
                        FinancialLedger.objects.create(
                            activity=activity,
                            farm=farm,
                            account_code=FinancialLedger.ACCOUNT_ACCUM_DEPRECIATION,
                            debit=Decimal("0"),
                            credit=machinery_cost,
                            description=f"إهلاك آلة {asset.name} إجباري بناءً على {hours} ساعة عمل",
                            currency=currency,
                            idempotency_key=f"ACC_DEP_{activity.id}_{timezone.now().timestamp()}"
                        )

        # 4. Overhead Cost (Allocated)
        overhead_cost = Decimal("0.0000")
        # Allocation Driver: Planted Area (Hectares)
        # Only for Planting/Service activities that imply area coverage
        # For simplicity in Phase 3, we check if activity has planting_details
        if hasattr(activity, 'planting_details'):
            # m2 to Hectare
            area_m2 = activity.planting_details.planted_area_m2 or Decimal("0")
            area_ha = (area_m2 * Decimal("0.0001")).quantize(Decimal("0.000001"))
            
            # Get Config
            config = CostConfiguration.objects.filter(farm=activity.log.farm).first()
            if config:
                rate = config.overhead_rate_per_hectare
                overhead_cost += area_ha * rate

        # Quantize to 4 decimals to satisfy database constraints
        total_cost = (
            labor_cost + material_cost + machinery_cost + overhead_cost + wastage_cost
        ).quantize(Decimal("0.0000"))

        # Update Activity Cache
        activity.cost_labor = labor_cost.quantize(Decimal("0.0000"))
        activity.cost_materials = material_cost.quantize(Decimal("0.0000"))
        activity.cost_machinery = machinery_cost.quantize(Decimal("0.0000"))
        activity.cost_overhead = overhead_cost.quantize(Decimal("0.0000"))
        activity.cost_wastage = wastage_cost.quantize(Decimal("0.0000"))
        activity.cost_total = total_cost
        activity.save(update_fields=[
            'cost_labor', 'cost_materials', 'cost_machinery', 'cost_overhead', 'cost_wastage', 'cost_total'
        ])

        # Create Snapshot
        snapshot = ActivityCostSnapshot.objects.create(
            activity=activity,
            crop_plan=activity.crop_plan,
            task=activity.task,
            cost_labor=labor_cost,
            cost_materials=material_cost,
            cost_machinery=machinery_cost,
            cost_overhead=overhead_cost,
            cost_wastage=wastage_cost,
            cost_total=total_cost,
            currency=CostingService._resolve_currency(activity)
        )

        return snapshot
