import os
import django
from decimal import Decimal

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
django.setup()

from smart_agri.core.models.farm import Farm, Location, Task
from smart_agri.core.models.crop import Crop, CropVariety
from smart_agri.core.models.activity import DailyLog, Activity
from smart_agri.core.models.tree import LocationTreeStock
from smart_agri.core.services.inventory.service import TreeInventoryService
from django.contrib.auth import get_user_model
from django.utils import timezone

def plant_trees():
    User = get_user_model()
    admin_user = User.objects.filter(is_superuser=True).first()

    farm = Farm.objects.filter(name__icontains="مزرعة").first()
    if not farm:
        print("لم يتم العثور على مزرعة.")
        return

    location = Location.objects.filter(farm=farm).first()
    if not location:
        print("لم يتم العثور على مواقع للمزرعة.")
        return

    crop = Crop.objects.filter(name__icontains="نخيل").first() or Crop.objects.filter(is_perennial=True).first()
    if not crop:
        print("لم يتم العثور على محصول نخيل أو أشجار معمرة.")
        return

    variety = CropVariety.objects.filter(crop=crop).first()
    if not variety:
        print("لم يتم العثور على أصناف تابعة للمحصول.")
        return

    task = Task.objects.filter(name__icontains="زراعة").first() or Task.objects.filter(is_active=True).first()

    print(f"Planting 50 {variety.name} trees at {location.name} in {farm.name}...")

    log = DailyLog.objects.create(
        farm=farm,
        log_date=timezone.now().date(),
        supervisor=admin_user,
        status='approved'
    )

    activity = Activity.objects.create(
        log=log,
        location=location,
        task=task,
        crop=crop,
        variety=variety,
        tree_count_delta=50,
        note="Test planting entry by AI Agent",
        recorded_by=admin_user
    )

    # Invoking the inventory service to reconcile the stock
    TreeInventoryService.record_event_from_activity(activity=activity)

    stock = LocationTreeStock.objects.filter(location=location, crop_variety=variety).first()
    if stock:
        print(f"✅ بنجاح! تم إضافة عدد {stock.current_tree_count} شجرة '{variety.name}' التابعة لمحصول '{crop.name}' في '{location.name}' التابع لـ '{farm.name}'.")
    else:
        print("❌ لم يتم العثور على تحديث الرصيد.")

if __name__ == "__main__":
    plant_trees()
