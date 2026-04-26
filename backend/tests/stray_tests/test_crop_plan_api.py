import os
import sys
import django

sys.path.append(r'c:\tools\workspace\Agre_ERP_2027-main\backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()
client = APIClient()
client.force_authenticate(user=User.objects.first())

payload = {
    'farm': 1,
    'crop': 1,
    'name': 'Auto Test Plan 6',
    'start_date': '2026-06-01',
    'end_date': '2026-10-01',
    'expected_yield': '5000',
    'season': '',  # Empty season
    'currency': 'YER',
    'location_ids': [1] # Adding a location to see if it causes 500
}

try:
    response = client.post('/api/v1/crop-plans/', payload, format='json', HTTP_X_IDEMPOTENCY_KEY='test-idemp-1166')
    print('STATUS:', response.status_code)
    print('DATA:', response.data)
except Exception as e:
    import traceback
    traceback.print_exc()
