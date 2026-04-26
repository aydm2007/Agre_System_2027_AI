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

from smart_agri.core.models import Farm, Asset

def seed_wells_to_all_farms():
    farms = Farm.objects.filter(deleted_at__isnull=True)
    count = 0
    for farm in farms:
        # Check if it has a well
        has_well = Asset.objects.filter(farm=farm, category="Well", deleted_at__isnull=True).exists()
        if not has_well:
            Asset.objects.create(
                farm=farm, 
                name=f"بئر ارتوازي افتراضي - {farm.name}", 
                category="Well", 
                asset_type="deep_well", 
                purchase_value=Decimal('10000000.00'),
                status="ACTIVE"
            )
            count += 1
            print(f"✅ Added Default Well to Farm: {farm.name}")
    print(f"Total new wells added: {count}")

if __name__ == '__main__':
    seed_wells_to_all_farms()
