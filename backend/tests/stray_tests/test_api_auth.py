import os
import json
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from smart_agri.core.api.viewsets.crop import CropVarietyViewSet
from django.contrib.auth import get_user_model

User = get_user_model()
admin = User.objects.filter(is_superuser=True).first()

farm_id = 31
crop_id = 53
location_id = 108

factory = APIRequestFactory()
view = CropVarietyViewSet.as_view({'get': 'list'})

url = f'/api/v1/crop-varieties/?farm_id={farm_id}&crop_id={crop_id}&location_ids={location_id}'
request = factory.get(url)
force_authenticate(request, user=admin)
response = view(request)

if hasattr(response, 'data') and 'results' in response.data:
    for item in response.data['results']:
        if item.get('id') == 56:
            print("Full JSON:", json.dumps(item, ensure_ascii=False, indent=2))
            break
else:
    print("NO DATA")
