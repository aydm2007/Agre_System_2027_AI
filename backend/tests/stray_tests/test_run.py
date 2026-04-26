import os
import django
import sys
import traceback

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from django.contrib.auth import get_user_model
from smart_agri.core.api.reporting import request_advanced_report_job

factory = APIRequestFactory()
user = get_user_model().objects.filter(is_superuser=True).first()

from smart_agri.core.models.farm import Farm
farm = Farm.objects.first()

params = {
    "farm_id": farm.id,
    "start": "2026-10-01",
    "end": "2026-10-31",
    "include_details": "false"
}

request = factory.post("/api/v1/advanced-report/requests/", params, format="json")
force_authenticate(request, user=user)

try:
    resp = request_advanced_report_job(request)
    print("STATUS", getattr(resp, 'status_code', None))
except Exception as e:
    print("CRASHED EXCEPTION:")
    traceback.print_exc(file=sys.stdout)
