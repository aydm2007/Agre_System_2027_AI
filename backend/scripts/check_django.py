
import os
import sys
import django

sys.path.append(os.path.join(os.getcwd(), 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')

print("Setting up Django...")
try:
    django.setup()
    print("Django setup complete.")
except Exception as e:
    print(f"Django setup failed: {e}")
