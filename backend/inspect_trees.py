import os
import django
from datetime import date

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
django.setup()

from smart_agri.core.models import Farm, Crop, CropVariety, Location, FarmCrop
from smart_agri.core.models import BiologicalAssetCohort, LocationTreeStock

def inspect_farm21():
    print("=" * 70)
    print("Farm 21 - Perennial Tree Inventory Inspection")
    print("=" * 70)

    farm = Farm.objects.filter(id=21).first()
    if not farm:
        print("Farm 21 not found!")
        return

    print(f"\nFarm: {farm.name} (id={farm.id})")

    # Locations
    locations = Location.objects.filter(farm=farm, deleted_at__isnull=True)
    print(f"\nLocations ({locations.count()}):")
    for loc in locations:
        print(f"  [{loc.id}] {loc.name}")

    # Farm Crops
    farm_crops = FarmCrop.objects.filter(farm=farm, deleted_at__isnull=True)
    print(f"\nFarm Crops ({farm_crops.count()}):")
    for fc in farm_crops:
        print(f"  [{fc.crop.id}] {fc.crop.name} (perennial={fc.crop.is_perennial})")

    # CropVarieties
    perennial_crops = [fc.crop for fc in farm_crops if fc.crop.is_perennial]
    print(f"\nPerennial Crops: {[c.name for c in perennial_crops]}")

    for crop in perennial_crops:
        varieties = CropVariety.objects.filter(crop=crop, deleted_at__isnull=True)
        print(f"\n  Varieties for '{crop.name}' ({varieties.count()}):")
        for v in varieties:
            print(f"    [{v.id}] {v.name}")

    # LocationTreeStock
    lts_qs = LocationTreeStock.objects.filter(
        location__farm=farm, deleted_at__isnull=True
    ).select_related('location', 'crop_variety')
    print(f"\nLocationTreeStock ({lts_qs.count()} records):")
    for lts in lts_qs:
        print(f"  loc=[{lts.location.id}] {lts.location.name} | "
              f"variety=[{lts.crop_variety_id}] {lts.crop_variety.name if lts.crop_variety else '?'} | "
              f"current_count={lts.current_tree_count}")

    # BiologicalAssetCohort
    try:
        cohorts = BiologicalAssetCohort.objects.filter(
            location__farm=farm, deleted_at__isnull=True
        ).select_related('location', 'crop_variety')
        print(f"\nBiologicalAssetCohorts ({cohorts.count()} records):")
        for c in cohorts:
            print(f"  loc=[{c.location.id}] {c.location.name} | "
                  f"variety={c.crop_variety.name if c.crop_variety else '?'} | "
                  f"alive={c.alive_count} | stage={c.growth_stage}")
    except Exception as e:
        print(f"\nBiologicalAssetCohort error: {e}")

    print("\n" + "=" * 70)

if __name__ == '__main__':
    inspect_farm21()
