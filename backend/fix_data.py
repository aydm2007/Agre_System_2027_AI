import os
import django
from datetime import date

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
django.setup()

from smart_agri.core.models import Crop, CropProduct, Farm, LaborRate, FarmCrop, CropPlan
from smart_agri.core.models import Location


def run_fix():
    print("=" * 60)
    print("Sardood Farm Fix Script")
    print("=" * 60)

    # ─── 1. Add CropProducts for all crops (one per crop if none exist) ─────
    print("\n[1] CropProducts...")
    crops = Crop.objects.all()
    for c in crops:
        existing = CropProduct.objects.filter(crop=c, deleted_at__isnull=True).count()
        if existing == 0:
            # CropProduct.save() auto-creates the linked Item using name+pack_uom
            cp = CropProduct(
                crop=c,
                name=f"منتج {c.name}",
                pack_uom="KG",
                is_primary=True,
            )
            cp.save()
            print(f"  ✓ Created CropProduct: {cp.name} (crop={c.name})")
        else:
            print(f"  - Already has {existing} product(s): {c.name}")

    # ─── 2. Add LaborRate for Farm 21 if none is active ──────────────────────
    print("\n[2] LaborRate for Farm 21...")
    farm = Farm.objects.filter(id=21).first()
    if not farm:
        print("  ✗ Farm 21 not found!")
    else:
        active_rates = LaborRate.objects.filter(
            farm=farm, deleted_at__isnull=True
        )
        if active_rates.exists():
            print(f"  - Already has {active_rates.count()} LaborRate(s) for Farm 21")
        else:
            lr = LaborRate(
                farm=farm,
                role_name="عامل يومي",
                daily_rate=6000,
                cost_per_hour=750,   # 6000 / 8 hours
                currency="YER",
                effective_date=date.today(),
            )
            lr.save()
            print(f"  ✓ Created LaborRate: {lr}")

    # ─── 3. Ensure Farm 21 has an ACTIVE CropPlan covering today ────────────
    print("\n[3] Active CropPlan for Farm 21...")
    if farm:
        today = date.today()
        active_plan = CropPlan.objects.filter(
            farm=farm,
            status="ACTIVE",
            start_date__lte=today,
            end_date__gte=today,
            deleted_at__isnull=True,
        ).first()

        if active_plan:
            print(f"  - Active plan exists: '{active_plan.name}' "
                  f"({active_plan.start_date} → {active_plan.end_date})")
        else:
            # Pick first crop linked to this farm
            farm_crop = FarmCrop.objects.filter(farm=farm, deleted_at__isnull=True).first()
            if farm_crop:
                plan = CropPlan(
                    farm=farm,
                    crop=farm_crop.crop,
                    name=f"خطة {farm_crop.crop.name} {today.year}",
                    start_date=date(today.year, 1, 1),
                    end_date=date(today.year, 12, 31),
                    status="ACTIVE",
                )
                plan.save()

                # Link all locations of this farm to the plan
                locations = Location.objects.filter(
                    farm=farm, deleted_at__isnull=True
                )
                if hasattr(plan, 'locations'):
                    plan.locations.set(locations)

                print(f"  ✓ Created Active CropPlan: '{plan.name}'")
                print(f"    Crop: {farm_crop.crop.name}, "
                      f"Locations: {locations.count()}")
            else:
                print("  ✗ No crop linked to Farm 21 — cannot create plan automatically.")

    print("\n" + "=" * 60)
    print("Fix script completed.")
    print("=" * 60)


if __name__ == "__main__":
    run_fix()
