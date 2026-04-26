import os
import sys
import django
from django.core.management import call_command

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.config.settings")

# Try to load .env manually
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass

django.setup()

print("Running makemigrations...")
call_command("makemigrations", "core", interactive=False)
print("Running migrate...")
call_command("migrate", interactive=False)
print("done")
