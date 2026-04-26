import os
import glob
import django
from django.db import connection
from django.core.management import call_command
import traceback

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
django.setup()

print("--- STEP 1: DELETING FILES ---")
files = [
    r"c:\tools\workspace\saradud2027\backend\smart_agri\core\migrations\0020_remove_cropplan_cropplan_unique_production_unit_and_more.py",
    r"c:\tools\workspace\saradud2027\backend\smart_agri\core\migrations\0021_remove_activity_foobar_and_more.py",
    r"c:\tools\workspace\saradud2027\backend\smart_agri\finance\migrations\0012_remove_actualexpense_deleted_at_and_more.py",
    r"c:\tools\workspace\saradud2027\backend\smart_agri\finance\migrations\0013_remove_actualexpense_foobar_and_more.py",
    r"c:\tools\workspace\saradud2027\backend\smart_agri\inventory\migrations\0012_remove_item_deleted_at_remove_item_deleted_by_and_more.py",
    r"c:\tools\workspace\saradud2027\backend\smart_agri\inventory\migrations\0013_remove_item_foobar_remove_iteminventory_foobar_and_more.py"
]

for f in files:
    try:
        if os.path.exists(f):
            os.remove(f)
            print(f"Deleted: {f}")
        else:
            print(f"File not found (OK): {f}")
    except Exception as e:
        print(f"FAILED to delete {f}: {e}")

print("\n--- STEP 2: CLEANING DB RECORDS ---")
migrations_to_delete = [
    ('core', '0020_remove_cropplan_cropplan_unique_production_unit_and_more'),
    ('core', '0021_remove_activity_foobar_and_more'),
    ('finance', '0012_remove_actualexpense_deleted_at_and_more'),
    ('finance', '0013_remove_actualexpense_foobar_and_more'),
    ('inventory', '0012_remove_item_deleted_at_remove_item_deleted_by_and_more'),
    ('inventory', '0013_remove_item_foobar_remove_iteminventory_foobar_and_more'),
]

try:
    with connection.cursor() as cursor:
        for app, name in migrations_to_delete:
            cursor.execute("DELETE FROM django_migrations WHERE app=%s AND name=%s", [app, name])
            if cursor.rowcount > 0:
                 print(f"Deleted DB record: {app}.{name}")
            else:
                 print(f"DB record not found (OK): {app}.{name}")
except Exception as e:
    print(f"DB Error: {e}")
    traceback.print_exc()

print("\n--- STEP 3: MAKEMIGRATIONS ---")
try:
    call_command("makemigrations", "core", "finance", "inventory")
    print("Makemigrations SUCCESS")
except Exception as e:
    print("Makemigrations FAILED")
    traceback.print_exc()
