import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from rest_framework.test import APIClient
from django.contrib.auth.models import User
from smart_agri.core.models.farm import FarmSettings

def test_api():
    client = APIClient()
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        print("No superuser found.")
        return
    client.force_authenticate(user=user)
    
    settings = FarmSettings.objects.first()
    if not settings:
        print("No settings found")
        return
        
    farm_id = settings.farm_id
    settings_id = settings.id
    print(f"Testing PATCH for settings ID: {settings_id}")
    
    current_mode = settings.strict_erp_mode
    new_mode = not current_mode
    
    response = client.patch(
        f'/api/v1/farm-settings/{settings_id}/', 
        {'strict_erp_mode': new_mode},
        format='json'
    )
    print(f"Response status: {response.status_code}")
    if response.status_code == 500:
         print(f"Exception info: {response.content}")
    else:
         print(f"Success! Mode changed to {new_mode}")

if __name__ == '__main__':
    test_api()
