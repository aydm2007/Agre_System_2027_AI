import os
import django
import sys
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from django.contrib.auth import get_user_model
from smart_agri.core.api.reporting import request_advanced_report_job

factory = APIRequestFactory()
user = get_user_model().objects.filter(is_superuser=True).first()

request = factory.post('/api/v1/advanced-report/requests/', {'farm_id': 6, 'start': '2026-03-01'}, format='json')
force_authenticate(request, user=user)

try:
    resp = request_advanced_report_job(request)
    print("STATUS", resp.status_code)
    print("DATA", getattr(resp, 'data', resp.content))
except Exception as e:
    traceback.print_exc()
