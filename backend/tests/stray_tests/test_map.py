import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from smart_agri.core.api.viewsets.crop import CropVarietyViewSet
from smart_agri.core.models.farm import Location

print("=== CHECKING LOCATION 1 API MAP ===")
loc = Location.objects.filter(name__icontains="موقع1").first()
if not loc:
    print("Location 1 not found!")
else:
    print(f"Location found: {loc.id} - {loc.name} (Farm: {loc.farm_id})")
    
    viewset = CropVarietyViewSet()
    # Mock request and context
    viewset.request = None
    
    # We only need crop_id and location_ids
    # from check_loc1.py, we know crop_id for Mango is around 62 or 58.
    # Let's pass the crop_id belonging to the cohort
    from smart_agri.core.models.inventory import BiologicalAssetCohort
    cohort = BiologicalAssetCohort.objects.filter(location=loc).first()
    if cohort:
        crop_id = cohort.crop_id
        print(f"Testing with crop_id: {crop_id}, location_ids: [{loc.id}]")
        
        map_result = viewset._build_variety_location_map(crop_id, [loc.id])
        print("Map Result:", map_result)
    else:
        print("No cohort found for location.")
