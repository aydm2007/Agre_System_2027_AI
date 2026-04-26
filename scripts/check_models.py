
import os
import django

print("Setting up Django...")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()
print("Django setup complete.")

print("Importing core models...")
from smart_agri.core.models import CropPlan, SoftDeleteModel
print("Core models imported.")

print("Importing sales models...")
from smart_agri.sales.models import Sale
print("Sales models imported.")

print("All good.")
