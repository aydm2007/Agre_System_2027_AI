import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from rest_framework.test import APIRequestFactory
from django.contrib.auth import get_user_model
from smart_agri.core.api.reporting import request_advanced_report_job

# Set up Request
User = get_user_model()
u = User.objects.filter(is_superuser=True).first()

factory = APIRequestFactory()
request = factory.post('/api/v1/advanced-report/requests/', {'farm_id': 1, 'report_type': 'profitability_pdf'}, format='json')
request.user = u

# Call API endpoint
print("Calling API...")
try:
    response = request_advanced_report_job(request)
    print("Status:", response.status_code)
    print("Data:", response.data)
except Exception as e:
    import traceback
    traceback.print_exc()
