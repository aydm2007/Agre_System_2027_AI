import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
django.setup()

from smart_agri.core.models.tree import LocationTreeStock
from smart_agri.core.models.inventory import BiologicalAssetCohort

print("=== LocationTreeStock Records ===")
for stock in LocationTreeStock.objects.select_related('location', 'crop_variety', 'crop_variety__crop').filter(deleted_at__isnull=True):
    print(f"  ID:{stock.id} | Location:{stock.location_id} ({stock.location}) | Variety:{stock.crop_variety_id} ({stock.crop_variety}) | Crop:{stock.crop_variety.crop_id} | Count:{stock.current_tree_count}")

print("\n=== BiologicalAssetCohort Records ===")
for c in BiologicalAssetCohort.objects.filter(deleted_at__isnull=True).select_related('location', 'variety', 'variety__crop'):
    print(f"  ID:{c.id} | Farm:{c.farm_id} | Location:{c.location_id} ({c.location}) | Variety:{c.variety_id} ({c.variety}) | Crop:{c.variety.crop_id if c.variety else 'N/A'} | Status:{c.status}")
