import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from smart_agri.core.models.inventory import BiologicalAssetCohort
from smart_agri.core.models.tree import LocationTreeStock
from smart_agri.core.models.farm import Location
from smart_agri.core.models.crop import CropVariety

print("=== CHECKING LOCATION 1 ===")
loc = Location.objects.filter(name__icontains="موقع1").first()
if not loc:
    print("Location 1 not found!")
else:
    print(f"Location found: {loc.id} - {loc.name} (Farm: {loc.farm_id})")
    
    # Check Cohorts
    print("\n--- Cohorts in this location ---")
    cohorts = BiologicalAssetCohort.objects.filter(location=loc)
    for c in cohorts:
        print(f"Cohort ID: {c.id}, Variety: {c.variety.name if c.variety else 'None'}, Qty: {c.quantity}, Status: {c.status}")
        
    # Check Stocks
    print("\n--- Tree Stocks in this location ---")
    stocks = LocationTreeStock.objects.filter(location=loc)
    for s in stocks:
        print(f"Stock ID: {s.id}, Variety: {s.crop_variety.name if s.crop_variety else 'None'}, Count: {s.current_tree_count}")

