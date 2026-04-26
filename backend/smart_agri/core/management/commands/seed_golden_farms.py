from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from smart_agri.core.models import (
    Farm, Location, Crop, Task, Asset, Employee, Item, Unit, 
    CropPlan, CropPlanBudgetLine, Season
)
from datetime import date

class Command(BaseCommand):
    help = "Seeds Golden Farms (Sardud & Jaroba) and cleans up others"

    def handle(self, *args, **kwargs):
        self.stdout.write("🌟 Starting Golden Farm Initialization...")

        with transaction.atomic():
            # 1. Cleanup Non-Golden Farms
            # We preserve 'Sardud' and 'Al-Jaroba' if they exist, or recreate them.
            # We soft-delete or flag others? For strict "cleaning", we might deactivate them.
            farms_to_keep = ["مزرعة سردود", "مزرعة الجروبة", "Sardud Farm", "Al-Jaroba Farm"]
            deleted_count = Farm.objects.exclude(name__in=farms_to_keep).update(is_active=False)
            self.stdout.write(f"🧹 Deactivated {deleted_count} other farms.")

            # 2. Sardud Farm (Mango/Banana)
            sardud, _ = Farm.objects.get_or_create(
                name="مزرعة سردود",
                defaults={"code": "GOLDEN-01", "total_area": 1500, "is_active": True}
            )
            self.seed_sardud_data(sardud)

            # 3. Al-Jaroba Farm (Grains/Wheat)
            jaroba, _ = Farm.objects.get_or_create(
                name="مزرعة الجروبة",
                defaults={"code": "GOLDEN-02", "total_area": 2000, "is_active": True}
            )
            self.seed_jaroba_data(jaroba)
            
            self.stdout.write(self.style.SUCCESS("✅ Golden Farms Initialized Successfully!"))

    def seed_sardud_data(self, farm):
        # Mango & Banana
        self.stdout.write(f"  📍 Seeding Sardud: {farm.name}")
        
        # Crops
        mango, _ = Crop.objects.get_or_create(name="مانجو (Mango)", defaults={"mode": "Tree"})
        banana, _ = Crop.objects.get_or_create(name="موز (Banana)", defaults={"mode": "Tree"})
        
        # Locations
        loc1, _ = Location.objects.get_or_create(farm=farm, name="مربع 1 - مانجو", defaults={"type": "Field", "area": 50})
        loc2, _ = Location.objects.get_or_create(farm=farm, name="مربع 2 - موز", defaults={"type": "Field", "area": 30})

        # Assets
        well, _ = Asset.objects.get_or_create(
            farm=farm, name="بئر ارتوازي - سردود", 
            defaults={"category": "Well", "operational_cost_per_hour": Decimal("1500")}
        )

        # Team
        Employee.objects.get_or_create(farm=farm, name="علي (مشرف سردود)", defaults={"role": "Supervisor", "shift_rate": 5000})
        Employee.objects.get_or_create(farm=farm, name="سالم (عامل ري)", defaults={"role": "Worker", "shift_rate": 2000})

        # Materials
        unit_kg, _ = Unit.objects.get_or_create(code="kg", name="كيلوجرام")
        Item.objects.get_or_create(
            name="سماد يوريا (Sardud)", 
            defaults={"group": "Fertilizer", "type": "Stock", "unit_price": Decimal("300"), "uom": unit_kg}
        )
        
        # Crop Plan (Budget)
        season, _ = Season.objects.get_or_create(name="2026", defaults={"start_date": date(2026,1,1), "end_date": date(2026,12,31)})
        plan, _ = CropPlan.objects.get_or_create(
            farm=farm, crop=mango, season=season, location=loc1,
            defaults={
                "name": "خطة مانجو 2026",
                "start_date": date(2026,1,1), "end_date": date(2026,12,31),
                "budget_total": Decimal("5000000"),
                "status": "APPROVED"
            }
        )

    def seed_jaroba_data(self, farm):
        # Wheat & Corn
        self.stdout.write(f"  📍 Seeding Jaroba: {farm.name}")

        # Crops
        wheat, _ = Crop.objects.get_or_create(name="قمح (Wheat)", defaults={"mode": "Seasonal"})
        
        # Locations
        loc1, _ = Location.objects.get_or_create(farm=farm, name="حقل 1 - قمح", defaults={"type": "Field", "area": 100})

        # Assets
        tractor, _ = Asset.objects.get_or_create(
            farm=farm, name="حراثة كبيرة - الجروبة",
            defaults={"category": "Machinery", "operational_cost_per_hour": Decimal("6000")}
        )

        # Team
        Employee.objects.get_or_create(farm=farm, name="محمد (مشرف الجروبة)", defaults={"role": "Supervisor", "shift_rate": 5500})
