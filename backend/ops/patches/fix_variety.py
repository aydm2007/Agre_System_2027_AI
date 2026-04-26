import os
import django
import sys

with open("C:\\tools\\workspace\\AgriAsset_v44\\backend\\output.txt", "w", encoding="utf-8") as f:
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
        django.setup()
        from smart_agri.core.models import CropVariety
        
        v = CropVariety.objects.filter(pk=56).first()
        if v:
            f.write(f"Found variety 56. Current crop_id: {v.crop_id}\n")
            if v.crop_id is not None and v.crop_id != 53:
                f.write(f"Changing from {v.crop_id} to 53 to match Mango crop\n")
                v.crop_id = 53
                v.save()
                f.write("Saved successfully.\n")
            elif v.crop_id == 53:
                f.write("crop_id is already 53.\n")
            else:
                f.write("crop_id is already None (Global).\n")
        else:
            f.write("Variety 56 not found.\n")
    except Exception as e:
        f.write(f"Error: {e}\n")
