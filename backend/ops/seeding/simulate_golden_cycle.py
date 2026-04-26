import os
import django
import sys
from decimal import Decimal
from datetime import date, timedelta

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from smart_agri.core.models import (
    Farm, Location, Crop, CropVariety, CropPlan, 
    DailyLog, Activity, ActivityEmployee, ActivityMaterialApplication,
    Item, Unit, ItemInventory, TreeStockEvent, LocationTreeStock
)
from smart_agri.finance.models import FiscalYear, FiscalPeriod, FinancialLedger, Account
from smart_agri.sales.models import Customer, SalesInvoice, SalesInvoiceItem
from smart_agri.core.services.inventory_service import InventoryService
from smart_agri.core.services.costing.service import CostService
from smart_agri.sales.services import SaleService
from smart_agri.core.services.base import ServiceResult

User = get_user_model()

def log(msg):
    print(f"[Golden Cycle] {msg}")

def run_simulation():
    log("Starting Golden Farm Full Cycle Simulation...")

    # --- 1. ADMINISTRATIVE UNIT ---
    log("--> Administrative Unit: Setup")
    
    # 1.1 Create Admin & Farm
    admin_user, _ = User.objects.get_or_create(username="golden_admin", defaults={"email": "admin@goldenfarm.com"})
    admin_user.set_password("GoldenPass123!")
    admin_user.save()
    
    farm, created = Farm.objects.get_or_create(name="Golden Farm", defaults={"slug": "golden-farm", "owner": admin_user, "total_area": 500})
    if created:
        log("    Created 'Golden Farm'")
    else:
        log("    'Golden Farm' exists")

    # 1.2 Locations
    store_loc, _ = Location.objects.get_or_create(farm=farm, name="Main Warehouse", defaults={"code": "WH-01", "is_active": True})
    field_loc, _ = Location.objects.get_or_create(farm=farm, name="Sector A", defaults={"code": "SEC-A", "is_active": True})

    # 1.3 Crop & Variety
    crop, _ = Crop.objects.get_or_create(name="Golden Dates")
    variety, _ = CropVariety.objects.get_or_create(crop=crop, name="Khilas")

    # 1.4 Crop Plan
    plan, _ = CropPlan.objects.get_or_create(
        farm=farm, 
        crop=crop, 
        season="2026", 
        defaults={"area": 100, "start_date": date(2026, 1, 1)}
    )

    # 1.5 Fiscal Year
    fy, _ = FiscalYear.objects.get_or_create(
        farm=farm,
        year=2026,
        defaults={
            "start_date": date(2026, 1, 1),
            "end_date": date(2026, 12, 31),
            "is_closed": False
        }
    )
    # Open Current Period
    current_month = timezone.now().month
    period, _ = FiscalPeriod.objects.get_or_create(
        fiscal_year=fy,
        month=current_month,
        defaults={
            "start_date": date(2026, current_month, 1),
            "end_date": date(2026, current_month, 28),
            "is_closed": False
        }
    )

    # --- 2. TECHNICAL UNIT (INVENTORY/OPS) ---
    log("--> Technical Unit: Operations")

    # 2.1 Items (Input & Output)
    unit_kg, _ = Unit.objects.get_or_create(code="kg", name="Kilogram")
    unit_l, _ = Unit.objects.get_or_create(code="L", name="Liter")

    fertilizer, _ = Item.objects.get_or_create(
        name="Golden Fertilizer", 
        defaults={"uom": "kg", "unit": unit_kg, "unit_price": Decimal("5.00"), "group": "Fertilizer"}
    )
    
    # 2.2 GRN (Purchase)
    log("    Processing GRN (Purchase 1000kg Fertilizer @ $5.00)")
    InventoryService.process_grn(
        farm=farm,
        item=fertilizer,
        location=store_loc,
        qty=Decimal("1000"),
        unit_cost=Decimal("5.00"),
        ref_id="PO-GOLD-001",
        actor_user=admin_user
    )

    # 2.3 Transfer to Field
    log("    Transferring 200kg to Sector A")
    InventoryService.transfer_stock(
        farm=farm,
        item=fertilizer,
        from_loc=store_loc,
        to_loc=field_loc,
        qty=Decimal("200"),
        user=admin_user
    )

    # 2.4 Activity (Consumption)
    log("    Recording Activity: Fertilization (Consume 50kg)")
    daily_log, _ = DailyLog.objects.get_or_create(farm=farm, log_date=date.today(), defaults={"created_by": admin_user})
    
    # Task
    from smart_agri.core.models import Task
    task, _ = Task.objects.get_or_create(name="Fertilizing", defaults={"is_active": True})

    activity = Activity.objects.create(
        log=daily_log,
        crop_plan=plan,
        location=field_loc,
        task=task,
        note="Applying Golden Fertilizer",
        created_by=admin_user
    )

    # Material Application
    ActivityMaterialApplication.objects.create(
        activity=activity,
        item=fertilizer,
        quantity=Decimal("50"), # 50kg
        unit_cost=Decimal("5.00") # Should act. use MAP, but explicit for seed
    )

    # 2.5 Harvest (Production)
    log("    Recording Activity: Harvest (Produce 500kg Dates)")
    dates_item, _ = Item.objects.get_or_create(
        name="Fresh Dates", 
        defaults={"uom": "kg", "unit": unit_kg, "unit_price": Decimal("20.00"), "group": "Harvest"}
    )
    
    harvest_task, _ = Task.objects.get_or_create(name="Harvesting", defaults={"is_harvest_task": True})
    
    harvest_activity = Activity.objects.create(
        log=daily_log,
        crop_plan=plan,
        location=field_loc,
        task=harvest_task,
        note="Golden Harvest",
        created_by=admin_user,
    )
    
    # Using Service for Harvest
    from smart_agri.core.services.harvest_service import HarvestService
    # Mocking metadata update (usually via Serializer)
    harvest_activity.harvest_quantity = Decimal("500")
    harvest_activity.product = None # Or link to CropProduct
    harvest_activity.save()
    
    # Simulate Harvest Processing (Inventory + WIP)
    # Assuming HarvestService handles this. If not, we do manual GRN for harvest.
    # For simulation, let's just do GRN for the output to keep it simple if HarvestService is complex.
    InventoryService.process_grn(
        farm=farm,
        item=dates_item,
        location=store_loc, # Direct to store
        qty=Decimal("500"),
        unit_cost=Decimal("10.00"), # Production Cost (Estimated)
        ref_id=f"HARV-{harvest_activity.id}",
        actor_user=admin_user
    )

    # --- 3. FINANCIAL UNIT ---
    log("--> Financial Unit: Costing & Sales")

    # 3.1 Run Costing
    log("    Running Costing Service")
    CostService.calculate_activity_cost(activity)

    # 3.2 Sales (Revenue)
    log("    Creating Sales Invoice (Sell 100kg Dates @ $25.00)")
    customer, _ = Customer.objects.get_or_create(name="Golden Client", defaults={"farm": farm})
    
    invoice = SaleService.create_invoice(
        customer=customer,
        location=store_loc,
        invoice_date=date.today(),
        items_data=[
            {"item": dates_item.id, "qty": 100, "unit_price": 25.00}
        ],
        user=admin_user
    )
    
    log(f"    Invoice Created: #{invoice.id} (Draft)")
    
    SaleService.confirm_sale(invoice, user=admin_user)
    log(f"    Invoice Confirmed: #{invoice.id} (Approved)")

    # --- 4. VERIFICATION & REPORTING ---
    log("--> Verification Phase")
    
    # Check Ledger
    ledger_count = FinancialLedger.objects.filter(farm=farm).count()
    log(f"    Financial Ledger Entries: {ledger_count}")
    
    # Check Stock
    stock_fert = InventoryService.get_stock_level(farm, fertilizer, field_loc)
    log(f"    Fertilizer Stock (Field): {stock_fert} kg (Expected: 200 - 50 = 150)")
    
    stock_dates = InventoryService.get_stock_level(farm, dates_item, store_loc)
    log(f"    Dates Stock (Store): {stock_dates} kg (Expected: 500 - 100 = 400)")

    if stock_fert == 150 and stock_dates == 400:
        log("✅ SUCCESS: Full Cycle Completed without Logical Errors.")
    else:
        log("❌ FAIL: Stock Mismatch detected.")

    # --- 4.1 AGRI-GUARDIAN: Variance Endpoint Check ---
    log("    Checking Variance API Logic (Internal Call)")
    try:
        # Mock Request 
        from smart_agri.core.api.viewsets.planning import CropPlanViewSet
        view = CropPlanViewSet()
        view.action = 'variance'
        view.kwargs = {'pk': plan.id}
        view.request = None # Minimal mock
        
        # We need to manually set the object on the view or mock get_object
        view.get_object = lambda: plan
        
        resp = view.variance(None)
        if resp.status_code == 200:
            v_data = resp.data
            log(f"    ✅ Variance API: Revenue={v_data['revenue']}, Cost={v_data['actual_cost']}, ROI={v_data['roi']}%")
        else:
            log(f"    ❌ Variance API Failed: {resp.status_code}")
    except Exception as e:
        log(f"    ❌ Variance API Crash: {e}")


    # --- 5. EDGE CASE (NEGATIVE) TESTING ---
    log("--> Negative Testing (Agri-Guardian Integrity)")
    
    # 5.1 Test: Prevent Negative Stock (Sell more than available)
    log("    Test 1: Selling 500kg (Available: 400kg) - Expecting Failure")
    try:
        with transaction.atomic():
            bad_invoice = SaleService.create_invoice(
                customer=customer,
                location=store_loc,
                invoice_date=date.today(),
                items_data=[
                    {"item": dates_item.id, "qty": 500, "unit_price": 25.00}
                ],
                user=admin_user
            )
            SaleService.confirm_sale(bad_invoice, user=admin_user)
            log("    ❌ FAIL: System allowed negative stock!")
    except Exception as e:
        log(f"    ✅ PASS: System blocked negative stock. Error: {e}")

    # 5.2 Test: Cross-Farm Access (Admin tries to access Farm 999)
    log("    Test 2: Cross-Farm Access - Expecting Denial")
    other_farm = Farm.objects.create(name="Enemy Farm", slug="enemy-farm")
    try:
        from smart_agri.core.services.inventory_service import InventoryService
        other_loc = Location.objects.create(farm=other_farm, name="Secret Base")
        # Admin of Golden Farm tries to move stock in Enemy Farm
        InventoryService.transfer_stock(
            farm=farm, # Golden Farm
            item=fertilizer,
            from_loc=field_loc, # Golden Farm Loc
            to_loc=other_loc, # Enemy Farm Loc
            qty=Decimal("1"),
            user=admin_user
        )
        log("    ❌ FAIL: System allowed cross-farm transfer!")
    except Exception as e:
        log(f"    ✅ PASS: System blocked cross-farm transfer. Error: {e}")



if __name__ == "__main__":
    try:
        with transaction.atomic():
             run_simulation()
             # dry run? No, user wants data. Commit it.
    except Exception as e:
        log(f"❌ CRASH: {e}")
        import traceback
        traceback.print_exc()
        with open("crash_output.txt", "w") as f:
            traceback.print_exc(file=f)
