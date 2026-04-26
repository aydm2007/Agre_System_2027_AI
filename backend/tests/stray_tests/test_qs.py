import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from smart_agri.core.models.crop import CropVariety
from django.db.models import Q

crop_id = 53
farm_id = 31

qs = CropVariety.objects.select_related('crop').filter(deleted_at__isnull=True)
qs = qs.filter(Q(crop_id=crop_id) | Q(crop__isnull=True))
qs = qs.filter(Q(crop__farm_links__farm_id__in=[farm_id], crop__farm_links__deleted_at__isnull=True) | Q(crop__isnull=True))
qs = qs.filter(id__in=[56])

print(f"Final Count for variety 56: {qs.count()}")
for v in qs:
    print(f"  - {v.id}: {v.name}")
