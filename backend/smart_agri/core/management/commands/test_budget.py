from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from smart_agri.core.models import CropPlan, Task, CropPlanBudgetLine, Farm, Crop, Location

class Command(BaseCommand):
    help = 'Evaluates budget line integrity deeply.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("--- 🚀 Starting Budget Integrity Deep Analysis ---"))
        
        farm = Farm.objects.first()
        crop = Crop.objects.first()
        location = Location.objects.first()
        
        if not (farm and crop and location):
            self.stdout.write(self.style.ERROR("❌ Cannot run test: missing basic master data (Farm/Crop/Location)."))
            return

        plan = CropPlan.objects.filter(id=103).first() or CropPlan.objects.first()
        
        if not plan:
            self.stdout.write(self.style.ERROR("❌ Cannot run test: No CropPlan found."))
            return
            
        self.stdout.write(self.style.SUCCESS(f"✅ Found Target Plan: {plan.id} - {plan.name}"))

        task1, _ = Task.objects.get_or_create(name="Deep Integrity Task A - Prep", defaults={"crop": crop})
        task2, _ = Task.objects.get_or_create(name="Deep Integrity Task B - Harvest", defaults={"crop": crop})

        self.stdout.write(self.style.SUCCESS(f"✅ Using Tasks: [1] {task1.name}, [2] {task2.name}"))

        self.stdout.write(self.style.WARNING("\n--- 📝 TEST 1: Creating Clean Budget Lines ---"))
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
                self.stdout.write(self.style.SUCCESS(f"✅ Created Line 1 successfully: Task {task1.name} (Materials) - Total: 500 YER"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Failed to create Line 1: {e}"))

        self.stdout.write(self.style.WARNING("\n--- 📝 TEST 2: Testing Unique Constraint (crop_plan_id, task_id, category) ---"))
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
                self.stdout.write(self.style.ERROR("❌ FAILURE: System allowed duplicate Task+Category in the same plan. UNIQUE CONSTRAINT IS BROKEN."))
        except Exception as e:
            self.stdout.write(self.style.SUCCESS(f"✅ SUCCESS: System properly rejected duplicate Task+Category! Error caught: {type(e).__name__}"))
            
        self.stdout.write(self.style.WARNING("\n--- 📝 TEST 3: Creating Different Category for Same Task ---"))
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
                self.stdout.write(self.style.SUCCESS(f"✅ SUCCESS: Created Line 3 (Labor for same task). Total: 300 YER"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Failed to create Line 3: {e}"))

        self.stdout.write(self.style.WARNING("\n--- 📝 TEST 4: Modifying Values and Django save() hook check ---"))
        if line1:
            line1.refresh_from_db()
            line1.qty_budget = Decimal("20.000")
            line1.total_budget = line1.qty_budget * line1.rate_budget
            line1.save()
            line1.refresh_from_db()
            self.stdout.write(self.style.SUCCESS(f"✅ Modified Line 1: New Qty: {line1.qty_budget}, New Total: {line1.total_budget}"))

        self.stdout.write(self.style.WARNING("\n--- 🏆 OVERALL EVALUATION COMPLETED ---"))
