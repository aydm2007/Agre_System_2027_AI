from smart_agri.core.models.farm import Farm
from smart_agri.core.models.planning import CropPlan
from smart_agri.core.models.activity import Activity
from smart_agri.core.models.log import DailyLog

kept_names = ["الجروبة", "سردود"]

# Delete test data first to avoid integrity errors
farms_to_delete = Farm.objects.exclude(name__in=kept_names)
farm_ids = list(farms_to_delete.values_list('id', flat=True))

if farm_ids:
    print(f"Deleting {len(farm_ids)} test farms...")
    logs_deleted = DailyLog.objects.filter(farm_id__in=farm_ids).delete()
    plans_deleted = CropPlan.objects.filter(farm_id__in=farm_ids).delete()
    acts_deleted = Activity.objects.filter(log__farm_id__in=farm_ids).delete()
    farms_deleted = farms_to_delete.delete()
    print(f"Deleted {logs_deleted} logs, {plans_deleted} plans, {acts_deleted} activities, {farms_deleted} farms.")
else:
    print("No test farms found to delete.")

