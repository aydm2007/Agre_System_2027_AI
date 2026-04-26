import os
import django
import sys

print("Starting Django Setup...")
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
try:
    django.setup()
    print("Django Setup OK")
except Exception as e:
    print(f"Django Setup FAILED: {e}")
