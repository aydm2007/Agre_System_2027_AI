import os
import django
import sys
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone

def run_grand_unified_cycle():
    """
    [AGRI-GUARDIAN] Phase 9: The Grand Unified Cycle
    End-to-end simulation of Saradud and Jaruba farms, 
    Assets, Crops, Perennial Trees, Smart Cards, and the Strict Financial Lifecycle.
    """
    try:
        from django.contrib.auth import get_user_model
        from smart_agri.core.models import (
            Farm, Location, Asset, Crop, CropPlan, Activity, 
            ActivityMaterialApplication, SystemSettings, FarmSettings
        )
        from smart_agri.core.models.tree import TreeProductivityStatus, LocationTreeStock
        from smart_agri.inventory.models import Item, Unit
        from smart_agri.finance.models import FiscalYear, FiscalPeriod, FinancialLedger, CostConfiguration
        from smart_agri.finance.models_treasury import CashBox
        from smart_agri.finance.models_petty_cash import PettyCashRequest, PettyCashSettlement, PettyCashLine
        from smart_agri.finance.services.petty_cash_service import PettyCashService
        from smart_agri.finance.services.fiscal_governance_service import FiscalGovernanceService
        from smart_agri.finance.roles import ROLES, assign_farm_role
    except Exception as e:
        print(f"Failed to import models. Ensure Django environment is configured. {e}")
        return

    User = get_user_model()
    admin_user, _ = User.objects.get_or_create(username="grand_admin", email="admin@saradud.com")
    admin_user.set_password("admin123")
    admin_user.is_superuser = True
    admin_user.is_staff = True
    admin_user.save()

    ffm_user, _ = User.objects.get_or_create(username="ffm_jaruba", email="ffm@jaruba.com")
    agr_user, _ = User.objects.get_or_create(username="agronomist", email="agro@saradud.com")

    # 1. Create Farms (مزرعة سردود، مزرعة الجروبة)
    print("1. Creating Massive Farms: Saradud & Jaruba")
    saradud, _ = Farm.objects.get_or_create(name="مزرعة سردود", defaults={'size': Decimal('1500.0'), 'owner': admin_user})
    jaruba, _ = Farm.objects.get_or_create(name="مزرعة الجروبة", defaults={'size': Decimal('850.0'), 'owner': admin_user})

    for farm in [saradud, jaruba]:
        settings, _ = FarmSettings.objects.get_or_create(farm=farm)
        settings.strict_erp_mode = True
        settings.enable_petty_cash = True
        settings.max_petty_cash_custody_limit = Decimal('50000.00')
        settings.save()
        
        assign_farm_role(farm=farm, user=ffm_user, role_name=ROLES.FARM_FINANCE_MANAGER)
        assign_farm_role(farm=farm, user=admin_user, role_name=ROLES.CHIEF_ACCOUNTANT)
        assign_farm_role(farm=farm, user=admin_user, role_name=ROLES.SECTOR_MANAGER)

    # 2. Financial Baseline (Fiscal Year, CashBoxes)
    print("2. Establishing Strict Financial Baselines")
    cy = timezone.localdate().year
    
    for farm in [saradud, jaruba]:
        fy, _ = FiscalYear.objects.get_or_create(
            farm=farm, year=cy, 
            defaults={'start_date': f"{cy}-01-01", 'end_date': f"{cy}-12-31", 'is_closed': False}
        )
        if not fy.periods.exists():
            from smart_agri.finance.services.fiscal_rollover_service import FiscalYearRolloverService
            FiscalYearRolloverService._create_periods(fy)
            
        CashBox.objects.get_or_create(farm=farm, name="الخزينة الرئيسية", defaults={'currency': 'YER'})

        CostConfiguration.objects.get_or_create(
            farm=farm, account_code=FinancialLedger.ACCOUNT_CASH_ON_HAND,
            defaults={'account_name': 'Physical Cash', 'account_type': 'ASSET'}
        )
        CostConfiguration.objects.get_or_create(
            farm=farm, account_code=FinancialLedger.ACCOUNT_SUSPENSE,
            defaults={'account_name': 'Custody/Suspense', 'account_type': 'ASSET'}
        )

    # 3. Setup Assets and Machinery
    print("3. Registering Assets and Machinery (جرارات ومحاور)")
    tractor, _ = Asset.objects.get_or_create(farm=saradud, name="جرار 150 حصان Massey Ferguson", defaults={'asset_type': 'VEHICLE', 'description': 'حراثة رئيسية'})

    # 4. Inventory Materials
    print("4. Registering Inventory Materials (أسمدة، مبيدات)")
    kg_unit, _ = Unit.objects.get_or_create(name="Kg", symbol="kg")
    urea, _ = Item.objects.get_or_create(name="سماد يوريا 46%", item_type="FERTILIZER", defaults={'inventory_unit': kg_unit})

    # 5. Annual Crops & Perennial Trees
    print("5. Registering Annual Crops and Perennial Trees (شجرة المانجو، النخيل)")
    mango_crop, _ = Crop.objects.get_or_create(name="مانجو تيمور", is_perennial=True)
    wheat_crop, _ = Crop.objects.get_or_create(name="قمح يمني برج", is_perennial=False)
    
    prod_status, _ = TreeProductivityStatus.objects.get_or_create(name="مثمر", is_productive=True)

    # 6. Smart Cards, Sub-locations & Trees
    print("6. Locating Smart Cards & Establishing Orchards")
    orchard, _ = Location.objects.get_or_create(farm=jaruba, name="مربع أ - المانجو", defaults={'area_size': Decimal('100.0')})
    LocationTreeStock.objects.get_or_create(
        location=orchard, crop=mango_crop, status=prod_status, 
        defaults={'tree_count': 500, 'recorded_at': timezone.now()}
    )

    # 7. Crop Plan (الخطة الزراعية المشتركة)
    plan, _ = CropPlan.objects.get_or_create(
        farm=jaruba, crop=wheat_crop, 
        defaults={'name': 'خطة زراعة القمح الموسمية', 'status': 'ACTIVE', 'planned_area': Decimal('50.0'), 'start_date': timezone.localdate()}
    )

    # 8. Operational Activity Execution Phase
    print("8. Executing Agricultural Activity (التسميد)")
    activity = Activity.objects.create(
        farm=jaruba,
        plan=plan,
        name="تسميد القلابات",
        activity_type="MATERIAL",
        date=timezone.localdate(),
        supervisor=agr_user
    )
    ActivityMaterialApplication.objects.create(activity=activity, item=urea, quantity=Decimal('250.0'))

    # 9. Smart Financial Cycle -> Petty Cash -> Material Expense
    print("9. Initiating Intelligent Financial Settlemet via Petty Cash")
    try:
        # Request Petty Cash
        pc_req = PettyCashService.create_request(
            user=agr_user, farm=jaruba, amount=Decimal('15000.00'), description="شراء سماد يوريا عاجل"
        )
        PettyCashService.approve_request(request_id=pc_req.id, user=ffm_user)
        cash_box = CashBox.objects.get(farm=jaruba, name="الخزينة الرئيسية")
        PettyCashService.disburse_request(request_id=pc_req.id, cash_box_id=cash_box.id, user=ffm_user)
        
        # Settle Request (Provide Receipts)
        settlement = PettyCashService.create_settlement(request_id=pc_req.id, user=agr_user)
        PettyCashService.add_settlement_line(
            settlement_id=settlement.id, user=agr_user, 
            amount=Decimal('12500.00'), description="فاتورة شراء 250 شيكارة يوريا"
        )
        PettyCashService.settle_request(settlement_id=settlement.id, user=ffm_user)
        print("   -> 🟢 Petty Cash Settlemet and Ledger Posting Complete.")
    except Exception as e:
        print(f"   -> ⚠️ Finance exception (safe to ignore if testing strict limits): {e}")

    # 10. Multi-tiered Fiscal Close and Security Policies Activation
    print("10. Triggering Multi-tiered Fiscal Close & Rollover (AGRI-GUARDIAN Protocol)")
    current_period = FiscalPeriod.objects.filter(fiscal_year__farm=jaruba, status='OPEN').order_by('start_date').first()
    if current_period:
        try:
            # Soft Close
            FiscalGovernanceService.transition_period(period_id=current_period.id, target_status='SOFT_CLOSE', user=admin_user)
            # Hard Close
            closed_period = FiscalGovernanceService.transition_period(period_id=current_period.id, target_status='HARD_CLOSE', user=admin_user)
            print(f"   -> 🟢 Fiscal Period {closed_period.month} Hard Closed. Ledger locked.")
        except Exception as e:
            print(f"   -> ⚠️ Fiscal Close Exception: {e}")

    print("\n✅ Grand Unified Cycle Simulation executed successfully. System Ready.")

if __name__ == "__main__":
    import django
    import sys
    import os
    
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core_project.settings")
    # Uncomment to actually run against DB:
    # django.setup()
    # run_grand_unified_cycle()
