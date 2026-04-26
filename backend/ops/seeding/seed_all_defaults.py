import os
import sys
from decimal import Decimal
from django.db import transaction

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
import django
django.setup()

from smart_agri.core.models import Farm, Asset, Location

def seed_defaults_to_all_farms():
    farms = Farm.objects.filter(deleted_at__isnull=True)
    count_locs = 0
    count_wells = 0
    
    for farm in farms:
        # Check Location
        has_loc = Location.objects.filter(farm=farm, deleted_at__isnull=True).exists()
        if not has_loc:
            Location.objects.create(
                farm=farm, 
                name=f"موقع افتراضي - {farm.name}", 
                type="Field"
            )
            count_locs += 1
            print(f"✅ Added Default Location to Farm: {farm.name}")
            
        # Check Well
        has_well = Asset.objects.filter(farm=farm, category="Well", deleted_at__isnull=True).exists()
        if not has_well:
            Asset.objects.create(
                farm=farm, 
                name=f"بئر افتراضي - {farm.name}", 
                category="Well", 
                asset_type="deep_well", 
                purchase_value=Decimal('10000000.00'),
                status="ACTIVE"
            )
            count_wells += 1
            print(f"✅ Added Default Well to Farm: {farm.name}")
            
    print(f"Total new locations added: {count_locs}")
    print(f"Total new wells added: {count_wells}")

if __name__ == '__main__':
    seed_defaults_to_all_farms()
