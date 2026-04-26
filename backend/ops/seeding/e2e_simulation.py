import os
import sys
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
import django
django.setup()

from smart_agri.accounts.models import User
from smart_agri.core.models import Farm, Location, Asset, LocationWell

def run_phase_1_and_2():
    print("================================")
    print("🟢 Phase 1 & 2: Core Setup (Farms, Locations, Wells)")
    print("================================")
    
    with transaction.atomic():
        # Setup Users
        user, _ = User.objects.get_or_create(username="e2e_manager", defaults={"email": "manager@e2e.test", "is_active": True})
        
        # 1. Create Farm (Tenant)
        farm, created = Farm.objects.get_or_create(
            name="مزرعة تهامة النموذجية",
            defaults={
                "slug": "tihama-e2e",
                "region": "الحديدة",
                "area": Decimal('100.00'), # Medium Tier
                "zakat_rule": Farm.ZAKAT_HALF_TITHE # 5% الآبار
            }
        )
        print(f"✅ Farm: {farm.name} (Tier: Medium Area>50) - [{farm.zakat_rule}]")

        # 2. Create Locations
        loc1, _ = Location.objects.get_or_create(farm=farm, name="حقل الذرة الشمالي", defaults={"type": "Field"})
        loc2, _ = Location.objects.get_or_create(farm=farm, name="بستان المانجو", defaults={"type": "Orchard"})
        print(f"✅ Locations Created: {loc1.name}, {loc2.name}")

        # 3. Create Assets (Wells & Solar)
        well_asset, _ = Asset.objects.get_or_create(
            farm=farm, name="بئر ارتوازي #1", 
            defaults={
                "category": "Well", 
                "asset_type": "deep_well", 
                "purchase_value": Decimal('15000000.00'),
                "status": "ACTIVE"
            }
        )
        solar_asset, _ = Asset.objects.get_or_create(
            farm=farm, name="منظومة طاقة شمسية 50kW", 
            defaults={
                "category": "Solar", 
                "asset_type": "solar_panel", 
                "purchase_value": Decimal('20000000.00'),
                "useful_life_years": 10,
                "salvage_value": Decimal('2000000.00')
            }
        )
        print(f"✅ Assets Created: {well_asset.name} (Well), {solar_asset.name} (Solar)")

        # 4. Link Well to Location
        loc_well, _ = LocationWell.objects.get_or_create(
            location=loc1,
            asset=well_asset,
            defaults={
                "well_depth": Decimal('120.50'),
                "capacity_lps": Decimal('15.00'),
                "is_operational": True
            }
        )
        print(f"✅ Well Linked to Location: {loc_well}")

    return farm, user, loc1, loc2, well_asset, solar_asset

if __name__ == '__main__':
    run_phase_1_and_2()
