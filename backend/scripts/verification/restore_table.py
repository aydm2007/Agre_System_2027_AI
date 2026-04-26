
import os
import django
from django.db import connection, migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
django.setup()

from smart_agri.core.models import ActivityItem

def restore_table():
    print("🚑 Emergency Repair: Restoring 'core_activity_item'...")
    
    # 1. Check if table exists
    with connection.cursor() as cursor:
        table_name = ActivityItem._meta.db_table
        cursor.execute("SELECT to_regclass(%s)", [table_name])
        if cursor.fetchone()[0]:
            print(f"⚠️ Table '{table_name}' already exists. Skipping creation.")
            return

    # 2. Create Table
    print(f"🛠️ Creating table '{table_name}' from model definition...")
    try:
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(ActivityItem)
        print("✅ Table created successfully.")
    except Exception as e:
        print(f"❌ Failed to create table: {e}")

if __name__ == "__main__":
    restore_table()
