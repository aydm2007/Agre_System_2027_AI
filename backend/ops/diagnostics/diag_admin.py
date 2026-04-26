import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from smart_agri.core.models.crop import CropVariety
from django.db.models import Q

# Replicate EXACT live API logic step by step
print("=== Step 1: base qs ===")
qs = CropVariety.objects.select_related('crop').filter(deleted_at__isnull=True)
print("Count:", qs.count())

print("\n=== Step 2: crop_id filter (crop=53 OR crop=None) ===")
qs = qs.filter(Q(crop_id=53) | Q(crop__isnull=True))
print("Count:", qs.count())
for v in qs:
    print(f" - ID:{v.id}, Name:{v.name}, crop_id={v.crop_id}")

print("\n=== Step 3: farm_id filter (farm_id=31 OR crop=None) ===")
qs = qs.filter(Q(crop__farm_links__farm_id__in=[31], crop__farm_links__deleted_at__isnull=True) | Q(crop__isnull=True))
print("Count:", qs.count())
for v in qs:
    print(f" - ID:{v.id}, Name:{v.name}, crop_id={v.crop_id}")

print("\n=== Step 4: location filter (location_ids=108) ===")
# Call _build_variety_location_map with crop_id=53 and location_ids=[108]
from smart_agri.core.api.viewsets.crop import CropVarietyViewSet
viewset = CropVarietyViewSet()
from rest_framework.test import APIRequestFactory, force_authenticate
from django.contrib.auth import get_user_model
User = get_user_model()
admin = User.objects.get(username='admin')
factory = APIRequestFactory()
request = factory.get("/", {"crop_id": "53", "farm_id": "31", "location_ids": "108"})
force_authenticate(request, user=admin)
viewset.request = request
variety_location_map = viewset._build_variety_location_map("53", [108])
print("Map:", variety_location_map)
print("Map keys:", list(variety_location_map.keys()))

qs4 = qs.filter(id__in=variety_location_map.keys())
print("After location filter Count:", qs4.count())
for v in qs4:
    print(f" - ID:{v.id}, Name:{v.name}")
