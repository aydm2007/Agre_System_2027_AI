
import os
import django
import sys
from decimal import Decimal
from django.utils import timezone
from datetime import date

# Setup Django Environment
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from django.contrib.auth.models import User, Group
from smart_agri.core.models import Farm, Location, Crop, CropPlan, Season
from smart_agri.core.models.activity import Activity
from smart_agri.core.models.log import DailyLog
from smart_agri.core.models.hr import Employee, EmploymentCategory
from smart_agri.finance.models import CostConfiguration, BudgetClassification, SectorRelationship, WorkerAdvance
from smart_agri.inventory.models import Item, Unit, StockMovement, ItemInventory, ItemInventoryBatch, FuelLog

def log(msg):
    print(msg)
    try:
        with open('seeding.log', 'a', encoding='utf-8') as f:
            f.write(msg + '\n')
    except Exception:
        pass 

def seed_golden_farm():
    log("--- 🚜 STARTING GOLDEN FARM SEEDING (SARDUD & AL-JAROBA) - ARABIC FULL ---")

    # ------------------------------------------------------------------
    # PHASE 0: CLEANUP (Redundant if flushed, but good for safety)
    # ------------------------------------------------------------------
    log("🧹 PHASE 0: Cleaning old/test data... (Validating Empty via Flush)")
    # If run after flush, this does nothing mostly.
    
    # ------------------------------------------------------------------
    # PHASE 1: SUPERUSER
    # ------------------------------------------------------------------
    ibrahim, _ = User.objects.get_or_create(username='ibrahim')
    ibrahim.set_password('123456')
    ibrahim.is_staff = True
    ibrahim.is_superuser = True
    ibrahim.save()
    log("✅ User 'ibrahim' verified.")

    # ------------------------------------------------------------------
    # PHASE 2: FARMS (Sardud & Al-Jaroba) - ARABIC
    # ------------------------------------------------------------------
    sardud, _ = Farm.objects.get_or_create(
        name='مزرعة سردود',
        defaults={'slug': 'sardud', 'area': 500, 'region': 'تهامة', 'is_active': True}
    )
    if not sardud.slug: sardud.slug = 'sardud'; sardud.save()
    if not sardud.is_active: sardud.is_active = True; sardud.save()

    jaroba, _ = Farm.objects.get_or_create(
        name='مزرعة الجروبة',
        defaults={'slug': 'al-jaroba', 'area': 200, 'region': 'الجوف', 'is_active': True}
    )
    if not jaroba.slug: jaroba.slug = 'al-jaroba'; jaroba.save()
    if not jaroba.is_active: jaroba.is_active = True; jaroba.save()

    print(f"✅ Farms Active: {sardud.name}, {jaroba.name}")

    # ------------------------------------------------------------------
    # PHASE 3: SECTOR RELATIONSHIP (Axis 4)
    # ------------------------------------------------------------------
    SectorRelationship.objects.get_or_create(farm=sardud, defaults={'current_balance': 0})
    SectorRelationship.objects.get_or_create(farm=jaroba, defaults={'current_balance': 0})

    # ------------------------------------------------------------------
    # PHASE 4: LOCATIONS - ARABIC
    # ------------------------------------------------------------------
    loc_sardud_1, _ = Location.objects.get_or_create(farm=sardud, name="سردود - مربع أ", defaults={'type': 'Field'})
    loc_jaroba_1, _ = Location.objects.get_or_create(farm=jaroba, name="الجروبة - قطاع 1", defaults={'type': 'Field'})

    # ------------------------------------------------------------------
    # PHASE 5: CROPS & ITEMS & UNITS
    # ------------------------------------------------------------------
    kg, _ = Unit.objects.get_or_create(code="KG", defaults={'name': 'كيلوجرام', 'category': Unit.CATEGORY_MASS})
    liter, _ = Unit.objects.get_or_create(code="L", defaults={'name': 'لتر', 'category': Unit.CATEGORY_VOLUME})

    mango, _ = Crop.objects.get_or_create(name="مانجو", defaults={'max_yield_per_ha': 15})
    banana, _ = Crop.objects.get_or_create(name="موز", defaults={'max_yield_per_ha': 20})
    wheat, _ = Crop.objects.get_or_create(name="قمح", defaults={'max_yield_per_ha': 4})

    # Items
    diesel_item, _ = Item.objects.get_or_create(name="ديزل", defaults={'unit_price': 500, 'uom': 'L', 'unit': liter, 'group': 'Fuel'})
    
    # Mango Fruit Product
    mango_item, _ = Item.objects.get_or_create(name="ثمار مانجو", defaults={'unit_price': 1200, 'uom': 'KG', 'unit': kg, 'group': 'Produce'})

    # ------------------------------------------------------------------
    # PHASE 6: SEASON
    # ------------------------------------------------------------------
    season_2026, _ = Season.objects.get_or_create(
        name="Season 2026",
        defaults={'start_date': '2026-01-01', 'end_date': '2026-12-31', 'is_active': True}
    )

    # ------------------------------------------------------------------
    # PHASE 7: USERS & ROLES
    # ------------------------------------------------------------------
    # (Users are backend identifiers - keeping English is safer for login, but Display Names can be Arabic in future)
    roles = {
        'manager': 'Manager',
        'acct': 'Chief Accountant',
        'tech': 'Technical Officer',
        'sup': 'Site Supervisor',
        'cash': 'Cashier'
    }
    
    farm_users = {
        'sardud': sardud,
        'jaroba': jaroba
    }

    for farm_key, farm_obj in farm_users.items():
        for role_key, role_name in roles.items():
            username = f"{role_key}_{farm_key}"
            user, created = User.objects.get_or_create(username=username)
            if created or not user.check_password('123456'):
                user.set_password('123456')
                user.first_name = role_name
                user.last_name = farm_obj.name
                user.save()
    
    log("✅ Users & Roles verified.")

    # ------------------------------------------------------------------
    # PHASE 7.5: EMPLOYEES (For Admin Cycle)
    # ------------------------------------------------------------------
    ali_worker, _ = Employee.objects.get_or_create(
        employee_id="SARDUD-001",
        defaults={
            'farm': sardud,
            'first_name': "علي",
            'last_name': "السردودي",
            'role': Employee.TYPE_WORKER,
            'category': EmploymentCategory.CASUAL,
            'payment_mode': 'SURRA',
            'shift_rate': Decimal('5000.0000'),
            'guarantor_name': "Sheikh Ahmed"
        }
    )
    # Ensure update if exists
    if ali_worker.first_name != "علي":
        ali_worker.first_name = "علي"
        ali_worker.last_name = "السردودي"
        ali_worker.save()

    log(f"✅ Employee Created: {ali_worker.first_name} {ali_worker.last_name}")

    # ------------------------------------------------------------------
    # PHASE 8: FINANCE & BUDGETS
    # ------------------------------------------------------------------
    CostConfiguration.objects.get_or_create(farm=sardud, defaults={'overhead_rate_per_hectare': Decimal('5000'), 'currency': 'YER'})
    CostConfiguration.objects.get_or_create(farm=jaroba, defaults={'overhead_rate_per_hectare': Decimal('3000'), 'currency': 'YER'})
    
    # Budget Codes
    fuel_code, _ = BudgetClassification.objects.get_or_create(code="2111", defaults={'name_ar': "محروقات"})
    labor_code, _ = BudgetClassification.objects.get_or_create(code="1000", defaults={'name_ar': "أجور عمال"})

    log("✅ Financial Config & Budget Codes verified.")

    # ------------------------------------------------------------------
    # PHASE 9: CROP PLANS
    # ------------------------------------------------------------------
    CropPlan.objects.get_or_create(farm=sardud, season=season_2026, crop=mango, defaults={'area': 50, 'location': loc_sardud_1})
    CropPlan.objects.get_or_create(farm=jaroba, season=season_2026, crop=wheat, defaults={'area': 30, 'location': loc_jaroba_1})
    log("✅ Crop Plans Initialized.")

    log("✅ SEEDING COMPLETE: Sardud & Al-Jaroba are ready.")

if __name__ == '__main__':
    seed_golden_farm()
