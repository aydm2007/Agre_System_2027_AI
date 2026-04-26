import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from smart_agri.inventory.models import LocationTreeStock, BiologicalAssetCohort
from smart_agri.core.models.location import Location

print("--- LocationTreeStock counts ---")
stocks = LocationTreeStock.objects.filter(current_tree_count__gt=0).values('location__farm_id', 'location_id', 'crop_variety__crop_id', 'crop_variety_id')
print(f"Total non-zero stocks: {stocks.count()}")
if stocks.exists():
    print(stocks.first())

print("\n--- BiologicalAssetCohort counts ---")
cohorts = BiologicalAssetCohort.objects.filter(deleted_at__isnull=True).values('farm_id', 'location_id', 'crop_id', 'variety_id')
print(f"Total active cohorts: {cohorts.count()}")
if cohorts.exists():
    print(cohorts.first())
