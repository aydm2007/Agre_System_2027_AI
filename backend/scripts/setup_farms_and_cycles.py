import os
import sys
import django
from decimal import Decimal
from datetime import date, timedelta

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from django.utils import timezone

from smart_agri.core.models import (
    Farm, Location, Crop, CropVariety, CropPlan, 
    DailyLog, Activity, ActivityItem, ActivityMaterialApplication,
    Item, Unit, Task, Season
)
from smart_agri.finance.models import FiscalYear, FiscalPeriod, FinancialLedger
from smart_agri.core.models.settings import LaborRate
from smart_agri.sales.models import Customer
from smart_agri.core.services.inventory_service import InventoryService
from smart_agri.core.services.costing.service import CostService
from smart_agri.sales.services import SaleService

User = get_user_model()

def log(msg):
    print(f"[SETUP] {msg}")

def cleanup_farms():
    allowed_farm_names = ["مزرعة جولدن", "مزرعة سردود", "مزرعة الجروبة"]
    obsolete_farms = Farm.objects.exclude(name__in=allowed_farm_names)
    deleted_count = 0
    for farm in obsolete_farms:
        log(f"Deleting obsoleted farm: {farm.name}")
        farm.delete()
        deleted_count += 1
    log(f"Cleaned up {deleted_count} unnecessary farms.")

def setup_users_and_roles():
    # Setup Superuser
    su, created = User.objects.get_or_create(username="ibrahim", defaults={"email": "ibrahim@agri.com", "is_superuser": True, "is_staff": True})
    su.set_password("123456")
    su.save()
    log("Superuser 'ibrahim' created/updated.")

    # Setup Groups
    roles = [
        "مدير المزرعة",      # Farm Manager
        "رئيس الحسابات",     # Chief Accountant
        "المسئول الفني",     # Technical Manager
        "المشرف في الموقع",  # Site Supervisor
        "امين الصندوق"       # Cashier
    ]
    for role in roles:
        Group.objects.get_or_create(name=role)
    log(f"Created role groups: {roles}")

def create_farm_cycle(farm_name, crop_name, variety_name, item_name, harvest_name):
    farm, _ = Farm.objects.get_or_create(name=farm_name, defaults={"slug": farm_name.replace(" ", "-").lower(), "area": 100})
    log(f"--- Setting up Farm: {farm_name} ---")

    # Roles per farm
    manager, _ = User.objects.get_or_create(username=f"mgr_{farm.slug}", defaults={"email": f"mgr@{farm.slug}.com"})
    manager.set_password("123456")
    manager.groups.add(Group.objects.get(name="مدير المزرعة"))
    manager.save()
    farm.memberships.get_or_create(user=manager, defaults={"role": "Manager"})

    accountant, _ = User.objects.get_or_create(username=f"acc_{farm.slug}", defaults={"email": f"acc@{farm.slug}.com"})
    accountant.set_password("123456")
    accountant.groups.add(Group.objects.get(name="رئيس الحسابات"))
    accountant.save()
    farm.memberships.get_or_create(user=accountant, defaults={"role": "Accountant"})

    # Base locations
    store_loc, _ = Location.objects.get_or_create(farm=farm, name="المستودع الرئيسي", defaults={"code": f"WH-{farm.id}", "is_active": True, "type": "Store"})
    field_loc, _ = Location.objects.get_or_create(farm=farm, name="قطاع الانتاج", defaults={"code": f"SEC-{farm.id}", "is_active": True, "type": "Field"})

    # Setup Crops
    crop, _ = Crop.objects.get_or_create(name=crop_name)
    variety, _ = CropVariety.objects.get_or_create(crop=crop, name=variety_name)
    
    season_obj, _ = Season.objects.get_or_create(name="2026", defaults={"code": "2026", "start_date": date(2026,1,1), "end_date": date(2026,12,31)})
    plan, _ = CropPlan.objects.get_or_create(
        farm=farm, crop=crop, season=season_obj, location=field_loc, defaults={"area": 50, "start_date": date(2026, 1, 1)}
    )

    # Financial Config
    fy, _ = FiscalYear.objects.get_or_create(farm=farm, year=2026, defaults={"start_date": date(2026, 1, 1), "end_date": date(2026, 12, 31), "is_closed": False})
    current_month = timezone.now().month
    period, _ = FiscalPeriod.objects.get_or_create(fiscal_year=fy, month=current_month, defaults={"start_date": date(2026, current_month, 1), "end_date": date(2026, current_month, 28), "is_closed": False})

    # Items
    unit_kg, _ = Unit.objects.get_or_create(code="kg", name="Kilogram")
    fertilizer, _ = Item.objects.get_or_create(name=item_name, defaults={"uom": "kg", "unit": unit_kg, "unit_price": Decimal("300.00"), "group": "Fertilizer"})

    harvest_item, _ = Item.objects.get_or_create(name=harvest_name, defaults={"uom": "kg", "unit": unit_kg, "unit_price": Decimal("1500.00"), "group": "Harvest"})

    # Activity: Purchase
    log("  1. Finance/Inventory: Purchasing Fertilizer")
    # Add LaborRate for this farm
    LaborRate.objects.get_or_create(farm=farm, role_name="عامل يومي", defaults={"daily_rate": Decimal("3000.00"), "cost_per_hour": Decimal("500.00")})

    try:
        InventoryService.process_grn(farm=farm, item=fertilizer, location=store_loc, qty=Decimal("1000"), unit_cost=Decimal("300.00"), ref_id=f"PO-{farm.id}-001", actor_user=accountant)
    except Exception as e:
        log(f"  [WARN] GRN Failed (maybe already processed): {e}")

    # Transfer
    try:
        InventoryService.transfer_stock(farm=farm, item=fertilizer, from_loc=store_loc, to_loc=field_loc, qty=Decimal("200"), user=manager)
    except Exception as e:
        log(f"  [WARN] Transfer Failed: {e}")

    # Activity: Consumption
    log("  2. Technical: Applying Fertilizer")
    daily_log = DailyLog.objects.filter(farm=farm, log_date=date.today()).first()
    if not daily_log:
        daily_log = DailyLog.objects.create(farm=farm, log_date=date.today(), created_by=manager)
    task = Task.objects.filter(name="تسميد").first()
    if not task:
        task = Task.objects.create(name="تسميد", is_active=True)
    
    activity = Activity.objects.create(log=daily_log, crop_plan=plan, location=field_loc, task=task, note="تسميد دوري", created_by=manager)
    ActivityItem.objects.create(activity=activity, item=fertilizer, qty=Decimal("50"), cost_per_unit=Decimal("300.00"))

    # Running Costing
    log("  3. Finance: Costing Engine")
    CostService.calculate_activity_cost(activity)

    # Activity: Harvest & Sales
    log("  4. Sales: Harvest & Sell")
    harvest_task = Task.objects.filter(name="حصاد").first()
    if not harvest_task:
        harvest_task = Task.objects.create(name="حصاد", is_active=True, is_harvest_task=True)
    harvest_act = Activity.objects.create(log=daily_log, crop_plan=plan, location=field_loc, task=harvest_task, note="موسم حصاد", created_by=manager)
    harvest_act.harvest_quantity = Decimal("500")
    harvest_act.save()

    try:
        InventoryService.process_grn(farm=farm, item=harvest_item, location=store_loc, qty=Decimal("500"), unit_cost=Decimal("300.00"), ref_id=f"HARV-{harvest_act.id}", actor_user=manager)
    except Exception as e:
        log(f"  [WARN] Harvest GRN Failed: {e}")

    customer, _ = Customer.objects.get_or_create(name="سوق الجملة", defaults={"customer_type": "wholesaler"})
    
    try:
        invoice = SaleService.create_invoice(
            customer=customer, location=store_loc, invoice_date=date.today(),
            items_data=[{"item": harvest_item.id, "qty": 100, "unit_price": 1500.00}],
            user=accountant
        )
        SaleService.confirm_sale(invoice, user=manager)
        log(f"  Invoice Confirmed: #{invoice.id}")
    except Exception as e:
        log(f"  [WARN] Sales Invoice failed: {e}")

    log(f"--- Cycle Complete for Farm: {farm_name} ---")


def run():
    cleanup_farms()
    setup_users_and_roles()

    create_farm_cycle(
        farm_name="مزرعة جولدن",
        crop_name="مانجو جولد",
        variety_name="صنف أ",
        item_name="سماد يوريا جولد",
        harvest_name="مانجو فريش"
    )

    create_farm_cycle(
        farm_name="مزرعة سردود",
        crop_name="مانجو يمني",
        variety_name="تيمور",
        item_name="سماد يوريا يمني",
        harvest_name="مانجو سردود"
    )

    create_farm_cycle(
        farm_name="مزرعة الجروبة",
        crop_name="موز الجروبة",
        variety_name="كافنديش",
        item_name="سماد مركب",
        harvest_name="موز بلدي"
    )
    
    log("ALL DATA CYCLES GENERATED SUCCESSFULLY!")


if __name__ == "__main__":
    try:
        with transaction.atomic():
            run()
    except Exception as e:
        log(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
