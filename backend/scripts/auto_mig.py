import os
import sys
import django
from django.core.management import call_command

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
django.setup()

try:
    print("Running makemigrations with --noinput")
    call_command('makemigrations', 'core', 'finance', 'inventory', 'sales', 'accounts', interactive=False)
    print("Running migrate")
    call_command('migrate', interactive=False)
    print("Migrations applied successfully.")
except Exception as e:
    print(f"Error during migrations: {e}")
