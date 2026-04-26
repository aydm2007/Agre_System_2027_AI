import os
import sys
from decimal import Decimal
from django.db import transaction

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
import django
django.setup()

from smart_agri.users.models import User
from smart_agri.core.models import Farm, Location, Asset
from smart_agri.operations.models import CropPlan, DailyLog, ActivityEmployee, ActivityItem, Task as OpTask
from smart_agri.stock.models import Item, InventoryTransaction
from django.utils import timezone

def run_phase_3():
    print("================================")
    print("🚜 Phase 3: Operational Cycle (CropPlan, DailyLog, Equipment, Labor, Materials)")
    print("================================")
    
    farm = Farm.objects.filter(slug='tihama-e2e').first()
    if not farm:
        print("❌ Error: Farm not found! Phase 1/2 didn't run properly.")
        return
        
    print(f"✅ Loaded Farm: {farm.name}")
    user = User.objects.get(username="e2e_manager")
    location = Location.objects.filter(farm=farm, name="حقل الذرة الشمالي").first()
    solar = Asset.objects.filter(farm=farm, category="Solar").first()

    with transaction.atomic():
        # 1. Create Crop Plan
        plan, _ = CropPlan.objects.get_or_create(
            farm=farm,
            name="خطة الذرة الرفيعة 2026",
            defaults={
                "season": "الصيف",
                "start_date": timezone.now().date(),
                "end_date": getattr(timezone.now() + timezone.timedelta(days=90), 'date', lambda: (timezone.now() + timezone.timedelta(days=90)).date())(),
                "expected_yield_kg": Decimal('5000'),
                "planted_area": Decimal('20.0'),
                "status": "DRAFT",
                "budget_approved": Decimal('5000000.0') # 5 Million (Decimal)
            }
        )
        plan.status = "APPROVED"
        plan.save()
        print(f"✅ Crop Plan: {plan.name} (Budget: {plan.budget_approved})")

        # 2. Daily Log Task
        task, _ = OpTask.objects.get_or_create(
            farm=farm, 
            name="ري وتسميد أولي",
            defaults={"category": "Irrigation"}
        )
        log, created = DailyLog.objects.get_or_create(
            farm=farm,
            date=timezone.now().date(),
            task=task,
            defaults={
                "crop_plan": plan,
                "location": location,
                "status": "APPROVED",
                "notes": "E2E Test Log"
            }
        )
        print(f"✅ Daily Log Created for task: {task.name}")

        # 3. Labor (Surrah basis)
        emp1, _ = ActivityEmployee.objects.get_or_create(
            daily_log=log,
            employee_name="عامل مؤقت 1",
            defaults={
                "worker_type": "Casual/Contract", 
                "work_hours": Decimal('8.00'),
                "daily_rate": Decimal('5000.00'), # Surra rate per protocol
                "total_cost": Decimal('5000.00')
            }
        )
        print(f"✅ Labor Logged: Casual (Surrah: {emp1.daily_rate})")

        # 4. Material Stock Consumption (Diesel)
        diesel_item, _ = Item.objects.get_or_create(
            farm=farm, 
            name="ديزل", 
            defaults={"unit": "Liter", "category": "Fuel", "avg_cost": Decimal('1200.00')}
        )
        ActivityItem.objects.get_or_create(
            daily_log=log,
            item=diesel_item,
            defaults={
                "quantity": Decimal('50.00'),
                "unit_cost": diesel_item.avg_cost,
                "total_cost": Decimal('60000.00')
            }
        )
        print(f"✅ Material Consumed: {diesel_item.name} (-50 L)")

    print("================================")
    print("✅ Phase 3 Completed Successfully.")

if __name__ == '__main__':
    run_phase_3()
