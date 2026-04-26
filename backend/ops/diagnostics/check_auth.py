import os
import django
import requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

# Get the token directly from the live DB instead of using the Token model
from django.contrib.auth import get_user_model, authenticate
User = get_user_model()

user = User.objects.filter(username='admin').first()
print(f"User: {user}")

# Check what auth backend is used
from django.conf import settings
auth_classes = settings.REST_FRAMEWORK.get('DEFAULT_AUTHENTICATION_CLASSES', [])
print("Auth classes:", auth_classes)

# Check for JWT classes and get a token
url = "http://127.0.0.1:8000/"
# Look for auth endpoints  
import subprocess
result = subprocess.run(
    ["python", "manage.py", "show_urls"],
    cwd=r"C:\tools\workspace\AgriAsset_v44\backend",
    capture_output=True, text=True
)
# Print auth related URLs
for line in result.stdout.split('\n'):
    if 'auth' in line.lower() or 'login' in line.lower() or 'token' in line.lower() or 'jwt' in line.lower():
        print(line)
