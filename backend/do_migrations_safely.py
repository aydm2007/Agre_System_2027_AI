import os
import sys

print("Running migrations...")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
import django
django.setup()

from django.core.management import call_command
try:
    call_command("makemigrations", "finance")
    call_command("migrate", "finance")
    print("DONE")
except Exception as e:
    import traceback
    traceback.print_exc()
