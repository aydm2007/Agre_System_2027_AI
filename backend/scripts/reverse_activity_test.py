import os
import sys
from pathlib import Path
import django
import traceback

# Ensure project root is on sys.path so Django app modules can be imported
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from smart_agri.core.models import Activity
from smart_agri.core.services.tree_inventory import TreeInventoryService

PK = 158
try:
    activity = Activity.objects.get(pk=PK)
except Activity.DoesNotExist:
    print(f"Activity {PK} does not exist")
    raise SystemExit(0)

service = TreeInventoryService()
try:
    result = service.reverse_activity(activity=activity, user=None)
    print('REVERSE_OK')
    print(result)
except Exception as e:
    print('REVERSE_EXCEPTION')
    traceback.print_exc()
    raise
