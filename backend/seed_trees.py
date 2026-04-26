import os
import django
from datetime import date

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
django.setup()

from smart_agri.core.models import Farm, CropVariety, Location, FarmCrop
from smart_agri.core.models import LocationTreeStock, TreeProductivityStatus


def seed_tree_inventory():
    print("=" * 70)
    print("Seeding Tree Inventory for Farm 21 (Sardood)")
    print("=" * 70)

    farm = Farm.objects.filter(id=21).first()
    if not farm:
        print("Farm 21 not found!")
        return

    # Get or create a default productivity status
    productive_status, _ = TreeProductivityStatus.objects.get_or_create(
        code="PRODUCTIVE",
        defaults={"name_en": "Productive", "name_ar": "منتج"}
    )

    # Location → Crop mapping based on location names
    location_crop_map = {
        "بستان موز": "موز",
        "بستان مانجو": "مانجو",
    }

    locations = Location.objects.filter(farm=farm, deleted_at__isnull=True)
    farm_crops = FarmCrop.objects.filter(
        farm=farm, deleted_at__isnull=True
    ).select_related('crop')

    perennial_crops = {fc.crop.name: fc.crop for fc in farm_crops if fc.crop.is_perennial}
    print(f"\nPerennial crops: {list(perennial_crops.keys())}")

    created_count = 0
    for location in locations:
        loc_name = location.name
        # Try to match location to crop
        matched_crop = None
        for loc_keyword, crop_name in location_crop_map.items():
            if loc_keyword in loc_name and crop_name in perennial_crops:
                matched_crop = perennial_crops[crop_name]
                break

        if not matched_crop:
            print(f"\n  [SKIP] {loc_name} - no perennial crop match")
            continue

        # Get varieties for this crop
        varieties = CropVariety.objects.filter(
            crop=matched_crop, deleted_at__isnull=True
        )
        print(f"\n  Location: [{location.id}] {loc_name} → Crop: {matched_crop.name}")

        for variety in varieties:
            # Check if stock already exists
            existing = LocationTreeStock.objects.filter(
                location=location,
                crop_variety=variety,
            ).first()

            if existing:
                print(f"    [EXISTS] {variety.name}: {existing.current_tree_count} trees")
                continue

            # Create stock record with sample tree counts
            tree_count = 200 if matched_crop.name == "موز" else 150
            stock = LocationTreeStock(
                location=location,
                crop_variety=variety,
                current_tree_count=tree_count,
                productivity_status=productive_status,
                planting_date=date(2020, 1, 1),
                source="seed_data",
                notes="بيانات أولية - تحديث عبر الإنجاز اليومي",
            )
            stock.save()
            print(f"    ✓ Created: {variety.name} = {tree_count} trees")
            created_count += 1

    print(f"\n✅ Done — Created {created_count} LocationTreeStock records")

    # Also ensure each perennial variety has location_ids so frontend can show it
    print("\n\nVerification — Current LocationTreeStock for Farm 21:")
    all_stocks = LocationTreeStock.objects.filter(
        location__farm=farm,
        deleted_at__isnull=True,
    ).select_related('location', 'crop_variety', 'crop_variety__crop')
    for s in all_stocks:
        print(f"  [{s.location.id}] {s.location.name} | "
              f"{s.crop_variety.name} ({s.crop_variety.crop.name}) | "
              f"count={s.current_tree_count}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    seed_tree_inventory()
