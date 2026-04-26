from decimal import Decimal, ROUND_HALF_UP

from smart_agri.core.models.farm import Asset
from smart_agri.core.services.asset_service import AssetService
from smart_agri.core.services.costing.policy import CostPolicy

class CostCalculator:
    """
    Pure calculation logic for activity costs.
    """
    
    @staticmethod
    def calculate_materials_cost(materials_queryset) -> Decimal:
        """Calculate total materials cost from a queryset of ActivityItem."""
        # Note: Queryset processing isn't strictly "pure", but we keep it focused on math aggregation here.
        # Ideally, caller passes a list of items. For now, adapting existing pattern.
        from django.db.models import Sum, F, DecimalField
        from django.db.models.functions import Coalesce
        
        materials_cost = materials_queryset.aggregate(
            total=Coalesce(Sum(F('qty') * F('cost_per_unit'), output_field=DecimalField()), Decimal('0'))
        )['total']
        return Decimal(materials_cost).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @staticmethod
    def calculate_daily_labor_cost(daily_rate, days_worked) -> Decimal:
        """
        Calculates cost based on 'Sura' (Daily Rate).
        """
        rate = CostPolicy.to_decimal(daily_rate, "Daily Rate")
        days = CostPolicy.to_decimal(days_worked, "Shifts/Days")

        # Yemen Standard: Round Half Up to 2 places (YER)
        total_cost = (rate * days).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return total_cost

    @staticmethod
    def calculate_labor_cost(activity, employees_queryset, labor_daily_rate: Decimal) -> Decimal:
        """Calculate labor cost based on employees or shifts."""
        from smart_agri.core.models.hr import EmploymentCategory
        
        if employees_queryset.exists():
            total_labor = Decimal("0.00")
            casual_count = 0
            for detail in employees_queryset:
                # [Omega-2028] Hourly Costing Override (Direct Billing Mode)
                if getattr(detail, "is_hourly", False):
                    h_worked = getattr(detail, "hours_worked", Decimal("0.00")) or Decimal("0.00")
                    h_rate = getattr(detail, "hourly_rate", Decimal("0.00")) or Decimal("0.00")
                    
                    if getattr(detail, "labor_type", None) == "CASUAL_BATCH":
                        w_count = Decimal(str(getattr(detail, "workers_count", 0) or 0))
                        row_cost = (w_count * h_worked * h_rate)
                    else:
                        # REGISTERED worker (usually 1 person per row)
                        row_cost = (h_worked * h_rate)
                    
                    total_labor += row_cost
                    casual_count += 1
                    continue

                if getattr(detail, "labor_type", None) == "CASUAL_BATCH":
                    casual_count += 1
                    total_labor += Decimal(detail.wage_cost or Decimal("0.00"))
                    continue

                employee = detail.employee
                if not employee or employee.category == EmploymentCategory.OFFICIAL:
                    continue
                    
                casual_count += 1
                if detail.wage_cost and detail.wage_cost > 0:
                    total_labor += detail.wage_cost
                else:
                    total_labor += (detail.surrah_share * (employee.shift_rate or Decimal("0.0000")))

            total_labor = total_labor.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            if casual_count == 0:
                return Decimal("0.00")
            
            return total_labor

        else:
            # Fallback to Supervisor Shifts (Sura)
            shifts = CostPolicy.to_decimal(getattr(activity, 'days_spent', Decimal("0")) or Decimal("0"), "Shifts")
            rate = labor_daily_rate if shifts > 0 else Decimal("0")
            return (shifts * rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @staticmethod
    def calculate_machine_cost(activity, machine_rate: Decimal, asset: Asset | None) -> Decimal:
        machine_ext = getattr(activity, 'machine_details', None)
        machine_hours = CostPolicy.to_decimal(
            machine_ext.machine_hours if machine_ext else (getattr(activity, 'machine_hours', Decimal("0")) or Decimal("0")),
            "Machine Hours",
        )
        
        solar_depreciation_cost = Decimal("0.0000")
        if asset and asset.category == "Solar" and machine_hours > 0:
            solar_depreciation_cost = AssetService.calculate_operational_solar_depreciation(asset, machine_hours)
            
        return ((machine_hours * machine_rate) + solar_depreciation_cost).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        ), solar_depreciation_cost

    @staticmethod
    def calculate_overhead_cost(activity, overhead_rate: Decimal) -> Decimal:
        planting_ext = getattr(activity, 'planting_details', None)
        data = activity.data if isinstance(activity.data, dict) else {}
        planted_area_value = (
            planting_ext.planted_area
            if planting_ext
            else data.get("planted_area", Decimal("0"))
        )
        planted_uom = (
            planting_ext.planted_uom
            if planting_ext
            else data.get("planted_uom", None)
        )
        planted_area = CostPolicy.to_decimal(planted_area_value, "Planted Area")
        
        from decimal import getcontext
        # Convert to hectares based on UOM (Yemeni-relevant units)
        uom = (planted_uom or '').strip().lower()
        if uom == 'm2':
            area_ha = getcontext().divide(planted_area, Decimal("10000"))
        elif uom in ('dunum', 'dunums'):
            area_ha = getcontext().divide(planted_area, Decimal("10"))
        elif uom == 'libnah':
            # لبنة ≈ 44.4 م² → 1 هكتار ≈ 225.2 لبنة
            area_ha = getcontext().divide(planted_area * Decimal("44.4"), Decimal("10000"))
        else:
            area_ha = planted_area  # assume hectares
        rate = overhead_rate if area_ha > 0 else Decimal("0")
        return (area_ha * rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
