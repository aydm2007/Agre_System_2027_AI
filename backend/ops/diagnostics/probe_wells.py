import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from django.test import RequestFactory
from smart_agri.users.models import User
from smart_agri.core.models import Farm, Location, Asset, LocationWell
from smart_agri.core.api.viewsets.farm import LocationWellViewSet, LocationViewSet, AssetViewSet
from smart_agri.core.api.serializers.farm import LocationWellSerializer

def probe():
    print("--- [LocationWells Probe] ---")
    
    # 1. Find a superuser or farm manager
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        print("No superuser found.")
        return
        
    print(f"Using user: {user.username}")
    
    # 2. Find a farm
    farm = Farm.objects.filter(deleted_at__isnull=True).first()
    if not farm:
        print("No farms found.")
        return
        
    print(f"Testing for Farm: {farm.name} (ID: {farm.id})")
    
    factory = RequestFactory()
    
    # 3. Simulate Assets.list({ farm_id, category: 'Well' })
    request_assets = factory.get(f'/api/assets/?farm_id={farm.id}&category=Well')
    request_assets.user = user
    asset_view = AssetViewSet.as_view({'get': 'list'})
    response_assets = asset_view(request_assets)
    print(f"\nAssets (category=Well) count: {len(response_assets.data.get('results', response_assets.data)) if hasattr(response_assets, 'data') else 0}")
    if hasattr(response_assets, 'data'):
        data = response_assets.data.get('results', response_assets.data)
        for a in data[:3]:
            print(f" - {a.get('id')}: {a.get('name')} (category: {a.get('category')})")
            
    # 4. Simulate Locations.list({ farm_id })
    request_locs = factory.get(f'/api/locations/?farm_id={farm.id}')
    request_locs.user = user
    loc_view = LocationViewSet.as_view({'get': 'list'})
    response_locs = loc_view(request_locs)
    print(f"\nLocations count: {len(response_locs.data.get('results', response_locs.data)) if hasattr(response_locs, 'data') else 0}")
    if hasattr(response_locs, 'data'):
        data = response_locs.data.get('results', response_locs.data)
        for d in data[:3]:
             print(f" - {d.get('id')}: {d.get('name')} (farm_id: {d.get('farm')})")
    
    # 5. Simulate LocationWells.list({ farm_id })
    request_lw = factory.get(f'/api/location-wells/?farm_id={farm.id}')
    request_lw.user = user
    lw_view = LocationWellViewSet.as_view({'get': 'list'})
    response_lw = lw_view(request_lw)
    print(f"\nLocationWells count: {len(response_lw.data.get('results', response_lw.data)) if hasattr(response_lw, 'data') else 0}")
    if hasattr(response_lw, 'data'):
        data = response_lw.data.get('results', response_lw.data)
        for d in data[:3]:
            print(f" - {d.get('id')}: Location {d.get('location_name')} -> Asset {d.get('asset_name')} (Status: {d.get('status')})")
            print(f"   [Raw Data Expected in Frontend] -> id: {d.get('id')}, location_id: {d.get('location_id')}, asset_id: {d.get('asset_id')}")

if __name__ == '__main__':
    probe()
