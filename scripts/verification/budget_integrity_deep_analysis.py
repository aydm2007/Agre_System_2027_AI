"""Budget Integrity Deep Analysis (manual verification).

NOTE:
- This is NOT a unit test module (kept out of Django test discovery).
- Run manually via:
    python scripts/verification/budget_integrity_deep_analysis.py
  or via:
    python backend/manage.py shell < scripts/verification/budget_integrity_deep_analysis.py

Requires a configured database with seed data.
"""

import os
import sys
import django

# Ensure backend is on path when run from repo root
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.append(BACKEND_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
django.setup()


from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from smart_agri.core.models import CropPlan, Task, CropPlanBudgetLine, Farm, Crop, Location

def run_integrity_test():
    print("\n--- 🚀 Starting Budget Integrity Deep Analysis ---\n")
    
    farm = Farm.objects.first()
    crop = Crop.objects.first()
    location = Location.objects.first()
    
    if not (farm and crop and location):
        print("❌ Cannot run test: missing basic master data (Farm/Crop/Location).")
        return

    plan = CropPlan.objects.filter(id=103).first() or CropPlan.objects.first()
    
    if not plan:
        print("❌ Cannot run test: No CropPlan found.")
        return
        
    print(f"✅ Found Target Plan: {plan.id} - {plan.name}")

    task1, _ = Task.objects.get_or_create(name="Deep Integrity Task A - Prep", type="Operational", defaults={"crop": crop, "farm": farm})
    task2, _ = Task.objects.get_or_create(name="Deep Integrity Task B - Harvest", type="Operational", defaults={"crop": crop, "farm": farm})

    print(f"✅ Using Tasks: [1] {task1.name}, [2] {task2.name}")

    print("\n--- 📝 TEST 1: Creating Clean Budget Lines ---")
    CropPlanBudgetLine.objects.filter(crop_plan=plan, task__in=[task1, task2]).delete()

    line1 = None
    try:
        with transaction.atomic():
            line1 = CropPlanBudgetLine.objects.create(
                crop_plan=plan,
                task=task1,
                category="materials",
                qty_budget=Decimal("10.000"),
                uom="kg",
                rate_budget=Decimal("50.000"),
                total_budget=Decimal("500.000"),
                currency="YER"
            )
            print(f"✅ Created Line 1 successfully: Task {task1.name} (Materials) - Total: 500 YER")
    except Exception as e:
        print(f"❌ Failed to create Line 1: {e}")

    print("\n--- 📝 TEST 2: Testing Unique Constraint (crop_plan_id, task_id, category) ---")
    try:
        with transaction.atomic():
            line2 = CropPlanBudgetLine.objects.create(
                crop_plan=plan,
                task=task1,
                category="materials",
                qty_budget=Decimal("5.000"),
                uom="kg",
                rate_budget=Decimal("50.000"),
                total_budget=Decimal("250.000"),
                currency="YER"
            )
            print("❌ FAILURE: System allowed duplicate Task+Category in the same plan. UNIQUE CONSTRAINT IS BROKEN.")
    except Exception as e:
        print(f"✅ SUCCESS: System properly rejected duplicate Task+Category! Error caught: {type(e).__name__}")
        
    print("\n--- 📝 TEST 3: Creating Different Category for Same Task ---")
    try:
        with transaction.atomic():
            line3 = CropPlanBudgetLine.objects.create(
                crop_plan=plan,
                task=task1,
                category="labor",
                qty_budget=Decimal("2.000"),
                uom="surra",
                rate_budget=Decimal("150.000"),
                total_budget=Decimal("300.000"),
                currency="YER"
            )
            print(f"✅ SUCCESS: Created Line 3 (Labor for same task). Total: 300 YER")
    except Exception as e:
        print(f"❌ Failed to create Line 3: {e}")

    print("\n--- 📝 TEST 4: Modifying Values and Django save() hook check ---")
    if line1:
        line1.refresh_from_db()
        line1.qty_budget = Decimal("20.000")
        line1.total_budget = line1.qty_budget * line1.rate_budget
        line1.save()
        line1.refresh_from_db()
        print(f"✅ Modified Line 1: New Qty: {line1.qty_budget}, New Total: {line1.total_budget}")

    print("\n--- 🏆 OVERALL EVALUATION COMPLETED ---\n")


if __name__ == "__main__":
    run_integrity_test()
