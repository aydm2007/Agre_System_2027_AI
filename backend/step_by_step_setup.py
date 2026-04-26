import os
import sys
import time

print("STEP 1: Setting up environment variable...")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
print("SUCCESS: Environment set.")

print("STEP 2: Importing django...")
try:
    import django
    print("SUCCESS: Django imported.")
except Exception as e:
    print(f"FAILURE: Could not import django: {e}")
    sys.exit(1)

print("STEP 3: Running django.setup()...")
start = time.time()
try:
    django.setup()
    print(f"SUCCESS: django.setup() completed in {time.time() - start:.2f}s.")
except Exception as e:
    print(f"FAILURE: django.setup() failed: {e}")
    sys.exit(1)

print("STEP 4: Testing database connection...")
from django.db import connection
try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    print("SUCCESS: Database connection verified.")
except Exception as e:
    print(f"FAILURE: Database connection failed: {e}")

print("STEP 5: Testing migration generation (dry run)...")
from django.core.management import call_command
try:
    call_command('makemigrations', 'core', dry_run=True, no_input=True)
    print("SUCCESS: makemigrations core (dry run) completed.")
except Exception as e:
    print(f"FAILURE: makemigrations core (dry run) failed: {e}")
