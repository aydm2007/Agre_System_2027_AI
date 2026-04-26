import os
import django
import sys
import traceback
import json

print("Step 1: Imports done")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
print("Step 2: DJANGO_SETTINGS_MODULE set")
try:
    import django
    from django.conf import settings
    settings.configure(default_settings="smart_agri.settings", DEBUG=True, CELERY_TASK_ALWAYS_EAGER=True)
    django.setup()
    print("Step 3: Django Setup Done")
except Exception as e:
    import django
    # configure isn't allowed if settings are already configured, just update it if setup works
    django.setup()
    from django.conf import settings
    settings.CELERY_TASK_ALWAYS_EAGER = True
    print("Step 3: Django Setup Done (Updated Eager)")
    sys.exit(1)

from rest_framework.test import APIRequestFactory, force_authenticate
from django.contrib.auth import get_user_model
try:
    from smart_agri.core.api.reporting import request_advanced_report_job
    print("Step 4: Reporting imported")
except Exception as e:
    print("CRASH IN IMPORTING REPORT", e)
    sys.exit(1)

print("Step 5: Factory creation")

factory = APIRequestFactory()
user = get_user_model().objects.filter(is_superuser=True).first()
if not user:
    print("Superuser not found.")
    sys.exit(1)

# Farm 6 or 1
from smart_agri.core.models.farm import Farm
farm = Farm.objects.first()

params = {
    "farm_id": farm.id,
    "start": "2024-01-01",
    "end": "2024-12-31",
    "include_details": "false"
}

request = factory.post("/api/v1/advanced-report/requests/", params, format="json")
force_authenticate(request, user=user)

try:
    resp = request_advanced_report_job(request)
    print("STATUS", resp.status_code)
    try:
        print("DATA", resp.data)
    except:
        print("DATA", resp.content)
except Exception as e:
    import traceback
    with open("crash_debug.txt", "w") as f:
        traceback.print_exc(file=f)
    print("CRASHED:", e)

