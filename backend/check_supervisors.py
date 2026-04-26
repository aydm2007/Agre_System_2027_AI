import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
django.setup()

from smart_agri.core.models import DailyLog, Farm, Item
from smart_agri.inventory.models import ItemInventory

def check():
    from smart_agri.core.models import DailyLog, Farm, Item, FarmCrop
    farm_id = 21
    logs = DailyLog.objects.filter(farm_id=farm_id)
    print(f"Farm 21 Logs: {logs.count()}")
    
    crops = list(FarmCrop.objects.filter(farm_id=farm_id).values_list("crop_id", "crop__name"))
    print(f"Farm 21 Crops: {crops}")
    supervisors = list(logs.values_list("supervisor_id", "supervisor__name", named=True).distinct())
    print(f"Supervisors: {supervisors}")
    
    # Check inventory for Item 10
    items = Item.objects.filter(id=10)
    for item in items:
        print(f"Item 10: {item.name}, Group: {item.group}")
        
    inv = ItemInventory.objects.filter(farm_id=farm_id, item_id=10)
    print(f"\nInventory for Item 10 (Farm 21):")
    for i in inv:
        loc_name = i.location.name if i.location else "None (Farm Store)"
        print(f"  Location: {loc_name}, Qty: {i.qty}")

    # Check CropMaterial
    from smart_agri.core.models import CropMaterial
    cms = CropMaterial.objects.filter(item_id=10)
    print(f"\nCropMaterial for Item 10: {cms.count()} records")
    for cm in cms:
        print(f"  Crop: {cm.crop.name}")

if __name__ == "__main__":
    check()
