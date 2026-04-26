import os
import django
from rest_framework.test import APIRequestFactory, force_authenticate

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from smart_agri.core.api.viewsets.crop import CropVarietyViewSet
from smart_agri.core.models import Crop, Farm, LocationTreeStock
from django.contrib.auth import get_user_model

User = get_user_model()
admin = User.objects.filter(is_superuser=True).first()

stock = LocationTreeStock.objects.filter(crop_variety__isnull=False).first()
if not stock:
    print("No LocationTreeStock found!")
    exit()

farm_id = stock.location.farm_id
crop_id = stock.crop_variety.crop_id
location_id = stock.location_id
variety_id = stock.crop_variety_id

print(f"Using Farm: {farm_id}, Crop: {crop_id}, Location: {location_id}, Variety: {variety_id}")

factory = APIRequestFactory()
view = CropVarietyViewSet.as_view({'get': 'list'})

url = f'/api/v1/crop-varieties/?farm_id={farm_id}&crop_id={crop_id}&location_ids={location_id}'
request = factory.get(url)
force_authenticate(request, user=admin)
response = view(request)

print("=== API RESPONSE WITH LOCATION ===")
print("Status:", response.status_code)
if hasattr(response, 'data'):
     print("Data:", response.data)

url_fallback = f'/api/v1/crop-varieties/?farm_id={farm_id}&crop_id={crop_id}'
request_fallback = factory.get(url_fallback)
force_authenticate(request_fallback, user=admin)
response_fallback = view(request_fallback)

print("\n=== API RESPONSE FALLBACK ===")
print("Status:", response_fallback.status_code)
if hasattr(response_fallback, 'data'):
     print("Data:", response_fallback.data)

