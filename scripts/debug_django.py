
import os
import sys
print("1. Starting Django Check...")
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')

import django
print("2. Importing Django...")
try:
    django.setup()
    print("3. Django Setup COMPLETE ✅")
    from django.contrib.auth.models import User
    c = User.objects.count()
    print(f"4. DB Accessible. User Count: {c}")
except Exception as e:
    print(f"❌ Django/DB Failure: {e}")
