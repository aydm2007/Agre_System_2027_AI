import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from smart_agri.core.models.crop import CropVariety

v = CropVariety.objects.filter(id=56).first()
if not v:
    print("Variety 56 NOT FOUND!")
else:
    print(f"Variety 56: {v.name}")
    print(f"  Crop ID: {v.crop_id}")
    print(f"  Deleted at: {v.deleted_at}")
    
    # Wait, what if the crop__farm_links logic is wrong?
    # Because 'crop__farm_links' points to FarmCrop, but it is a related name?
    # the related_name on FarmCrop is 'farm_links'?
    
    # Let's see all crops the variety belongs to
    print(f"  Crop Name: {v.crop.name}")
    
    qs = CropVariety.objects.filter(id=56)
    qs = qs.filter(crop__farm_links__farm_id__in=[31])
    print(f"  Count with crop__farm_links__farm_id__in=[31]: {qs.count()}")
    
    qs2 = CropVariety.objects.filter(id=56, crop__farm_links__deleted_at__isnull=True)
    print(f"  Count with crop__farm_links__deleted_at__isnull=True: {qs2.count()}")

    from smart_agri.core.models.crop import FarmCrop
    fc = FarmCrop.objects.filter(crop_id=v.crop_id, farm_id=31).first()
    print(f"  FarmCrop Object: {fc}, deleted_at={fc.deleted_at if fc else 'N/A'}")
