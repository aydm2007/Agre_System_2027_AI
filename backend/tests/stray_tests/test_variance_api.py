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

try:
    response = client.get('/api/v1/crop-plans/132/variance/')
    print('STATUS:', response.status_code)
    print('DATA:', response.data)
except Exception as e:
    import traceback
    traceback.print_exc()
