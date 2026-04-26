import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from django.contrib.auth import get_user_model
from smart_agri.core.api.activities import ActivityViewSet
from smart_agri.core.models import DailyLog, Farm

User = get_user_model()
admin = User.objects.filter(username='admin').first()

farm = Farm.objects.get(id=31)
log = DailyLog.objects.filter(farm=farm, log_date="2026-04-01").first()

if getattr(log, 'deleted_at', None):
    print("Log is deleted!")
    log.deleted_at = None
    log.save()
elif not log:
    log = DailyLog.objects.create(farm=farm, log_date="2026-04-01")

print(f"Testing with log {log.id}, deleted_at={log.deleted_at}")

payload = {
    "log": log.id,
    "farm": 31,
    "crop": 53,
    "locations": [108],
    "date": "2026-04-01",
    "task": None,
    "workers": [],
    "service_counts": [
        {
            "variety_id": 56,
            "location_id": 108,
            "service_count": 10,
            "notes": ""
        }
    ],
    "variety_id": 56,
    "activity_tree_count": 10,
}

factory = APIRequestFactory()
view = ActivityViewSet.as_view({'post': 'create'})
request = factory.post('/api/v1/activities/', payload, format='json')
request.META['HTTP_X_IDEMPOTENCY_KEY'] = 'test-idemp-999999'
force_authenticate(request, user=admin)

try:
    response = view(request)
    print("Status:", response.status_code)
    if hasattr(response, 'data'):
        print("Response:", json.dumps(dict(response.data), ensure_ascii=False, indent=2))
except Exception as e:
    import traceback
    traceback.print_exc()
    if hasattr(e, 'detail'):
        print("Exception detail:", e.detail)
