import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
import django
django.setup()

from django.test import RequestFactory
from smart_agri.core.api.viewsets.farm import AssetViewSet
from smart_agri.users.models import User
from smart_agri.core.models import Farm, Asset

def test_asset_endpoint():
    user = User.objects.get(username="e2e_manager")
    farm = Farm.objects.filter(slug='tihama-e2e').first()
    
    # 1. Check DB first
    assets = Asset.objects.filter(farm=farm, category="Well", deleted_at__isnull=True)
    print(f"DB Assets count for {farm.name} (Well): {assets.count()}")
    for a in assets:
        print(f" - ID: {a.id}, Name: {a.name}, Category: {a.category}, Status: {a.status}")

    # 2. Check API
    factory = RequestFactory()
    request = factory.get(f'/api/v1/assets/?farm_id={farm.id}&category=Well&page_size=500')
    request.user = user

    view = AssetViewSet.as_view({'get': 'list'})
    response = view(request)
    
    print(f"\nAPI Response Status: {response.status_code}")
    print(f"API Data Count: {len(response.data.get('results', [])) if isinstance(response.data, dict) else len(response.data)}")
    if isinstance(response.data, dict) and 'results' in response.data:
        for r in response.data['results']:
            print(f" - API Item: {r['id']} | {r['name']} | {r['category']}")
    else:
        for r in response.data:
            print(f" - API Item: {r['id']} | {r['name']} | {r['category']}")

if __name__ == '__main__':
    test_asset_endpoint()
