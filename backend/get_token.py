import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.filter(username='admin').first()
if user:
    token, _ = Token.objects.get_or_create(user=user)
    print(f"Token: {token.key}")
else:
    print("No admin user found.")
