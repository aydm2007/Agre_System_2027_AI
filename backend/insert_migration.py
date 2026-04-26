import os
import django
from django.db import connection
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
django.setup()

migrations_to_insert = [
    ('core', '0020_remove_cropplan_cropplan_unique_production_unit_and_more'),
    ('finance', '0012_remove_actualexpense_deleted_at_and_more'),
    ('inventory', '0012_remove_item_deleted_at_remove_item_deleted_by_and_more'),
]

with connection.cursor() as cursor:
    for app, name in migrations_to_insert:
        print(f"Checking if {app}.{name} exists...")
        cursor.execute("SELECT id FROM django_migrations WHERE app=%s AND name=%s", [app, name])
        row = cursor.fetchone()
        if row:
            print(f"{app}.{name} already recorded.")
        else:
            print(f"Inserting {app}.{name}...")
            cursor.execute(
                "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, %s)",
                [app, name, timezone.now()]
            )
            print(f"{app}.{name} inserted successfully.")
