import os
import django
import json
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from smart_agri.core.models import Location, Crop, LocationTreeStock
from smart_agri.core.models.inventory import BiologicalAssetCohort

def serializable(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)

def inspect_farm_21():
    farm_id = 21
    print(f"--- Inspection for Farm {farm_id} ---")
    
    locations = Location.objects.filter(farm_id=farm_id)
    print(f"Locations: {locations.count()}")
    for loc in locations:
        print(f"  [{loc.id}] {loc.name}")
        
    stocks = LocationTreeStock.objects.filter(location__farm_id=farm_id)
    print(f"\nLocationTreeStock: {stocks.count()}")
    for s in stocks:
        var_name = s.crop_variety.name if s.crop_variety else "N/A"
        print(f"  Stock: id={s.id}, loc={s.location_id}, var={s.crop_variety_id} ({var_name}), count={s.current_tree_count}")
        
    cohorts = BiologicalAssetCohort.objects.filter(farm_id=farm_id)
    print(f"\nBiologicalAssetCohort: {cohorts.count()}")
    for c in cohorts:
        var_name = c.variety.name if c.variety else "N/A"
        print(f"  Cohort: id={c.id}, loc={c.location_id}, var={c.variety_id} ({var_name}), qty={c.quantity}, status={c.status}")

    from smart_agri.core.models import Item
    try:
        item = Item.objects.get(id=10)
        print(f"\nItem 10: {item.name}")
    except Item.DoesNotExist:
        print("\nItem 10 does not exist")

if __name__ == "__main__":
    inspect_farm_21()
