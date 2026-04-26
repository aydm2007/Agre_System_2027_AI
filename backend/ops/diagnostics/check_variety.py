import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from smart_agri.core.models import CropVariety, Crop

variety_id = 56
crop_id = 53

v = CropVariety.objects.filter(pk=variety_id).select_related('crop').first()
c = Crop.objects.filter(pk=crop_id).first()

print(f"Variety 56: {v.name if v else 'NOT FOUND'}")
if v:
    print(f"Variety 56 crop_id: {v.crop_id}")
    print(f"Variety 56 crop_name: {v.crop.name if v.crop else 'GLOBAL (None)'}")

print(f"Crop 53: {c.name if c else 'NOT FOUND'}")

if v and v.crop_id is not None and v.crop_id != crop_id:
    print("\nFIXING DATA: Variety 56 has explicit wrong crop_id.")
    # Either clear it or set it to 53.
    # We will set it to None to make it global, or keep it depending on logic.
    # Let's see what it is first before fixing.
