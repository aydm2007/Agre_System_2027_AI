from decimal import Decimal
from django.db.models import Sum, Q, F
from django.conf import settings
from smart_agri.core.models.planning import CropPlan
from smart_agri.core.models.activity import Activity
from smart_agri.core.models.inventory import HarvestLot
from smart_agri.finance.models import FinancialLedger

class ProfitabilityService:
    """
    Commercial Logic Layer: Unit Economics & Profitability.
    Aggregates financial and operational data to answer: 
    "How much did this specific crop cycle really cost?"
    """

    @staticmethod
    def generate_crop_report(crop_plan: CropPlan):
        """
        Generates a comprehensive P&L for a specific Crop Plan.
        """
        
        # 1. Direct Costs (From Activities)
        # We use the snapshot/strict cost fields
        direct_costs = Activity.objects.filter(
            crop_plan=crop_plan,
            deleted_at__isnull=True
        ).aggregate(
            materials=Sum('cost_materials'),
            labor=Sum('cost_labor'),
            machinery=Sum('cost_machinery'),
            other=Sum('cost_overhead') # Activity-level specific overheads
        )
        
        # 2. Indirect Costs (Allocated Overheads from Ledger)
        allocated_overhead = FinancialLedger.objects.filter(
            crop_plan=crop_plan,
            account_code=FinancialLedger.ACCOUNT_OVERHEAD
        ).aggregate(total=Sum('debit'))['total'] or Decimal("0")

        # 3. Total Cost Calculation
        total_materials = direct_costs['materials'] or Decimal("0")
        total_labor = direct_costs['labor'] or Decimal("0")
        total_machinery = direct_costs['machinery'] or Decimal("0")
        total_direct_overhead = direct_costs['other'] or Decimal("0")
        
        total_cost = (
            total_materials + 
            total_labor + 
            total_machinery + 
            total_direct_overhead + 
            allocated_overhead
        )

        # 4. Yield / Production (Revenue Side)
        harvest_metrics = HarvestLot.objects.filter(
            crop_plan=crop_plan,
            deleted_at__isnull=True
        ).aggregate(
            total_qty=Sum('quantity')
        )
        
        # [Agri-Guardian] DB-Native Financial Aggregation (Fix 18)
        # Calculate Real Revenue & Cost from the Ledger (Source of Truth)
        from django.db.models.functions import Coalesce
        ledger_agg = FinancialLedger.objects.filter(
            crop_plan=crop_plan
        ).aggregate(
            total_revenue=Coalesce(Sum('credit'), Decimal('0.00')),
            # We use Activity breakdown for details, but Ledger for total verification?
            # For now, let's keep breakdown but ADD Revenue/Margin logic.
        )
        
        real_revenue = ledger_agg['total_revenue']
        profit = real_revenue - total_cost
        margin_percent = Decimal('0.00')
        if real_revenue > 0:
            from decimal import getcontext
            margin_percent = (getcontext().divide(profit, real_revenue) * 100).quantize(Decimal("0.01"))
        
        total_yield = harvest_metrics['total_qty'] or Decimal("0")
        
        # 5. Unit Economics (KPIs)
        cost_per_unit = Decimal("0")
        if total_yield > 0:
            from decimal import getcontext
            cost_per_unit = getcontext().divide(total_cost, total_yield)

        # Get area (use 'area' field which exists in CropPlan)
        area_m2 = Decimal(str(crop_plan.area or 0)) * 10000  # Convert hectares to m2
        cost_per_hectare = Decimal("0")
        if area_m2 > 0:
            from decimal import getcontext
            cost_per_hectare = getcontext().divide(total_cost, getcontext().divide(area_m2, Decimal("10000")))

        return {
            "plan_metadata": {
                "id": crop_plan.id,
                "crop": crop_plan.crop.name,
                "season": crop_plan.season.name if crop_plan.season else "N/A",
                "area_m2": area_m2,
            },
            "financials": {
                "currency": getattr(crop_plan, 'currency', getattr(settings, 'DEFAULT_CURRENCY', 'YER')),
                "total_cost": total_cost,
                "total_revenue": real_revenue,
                "net_profit": profit,
                "margin_percent": margin_percent,
                "breakdown": {
                    "materials": total_materials,
                    "labor": total_labor,
                    "machinery": total_machinery,
                    "allocated_overhead": allocated_overhead
                }
            },
            "production": {
                "total_yield": total_yield,
                "uom": "kg"  # Simplified, ideally dynamic
            },
            "kpis": {
                "cost_per_unit": cost_per_unit,  # e.g. Cost per kg
                "cost_per_hectare": cost_per_hectare
            }
        }

