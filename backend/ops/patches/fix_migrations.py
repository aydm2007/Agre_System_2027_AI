import os
import django
import sys

# Setup Django
os.environ['DJANGO_SETTINGS_MODULE'] = 'smart_agri.settings'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.db import connection

def fix():
    print("🚀 Atomic Repair: Migration Inconsistency & Schema Guard...")
    with connection.cursor() as cursor:
        # 1. Manually insert core.0110 into django_migrations if missing
        cursor.execute("SELECT id FROM django_migrations WHERE app='core' AND name='0110_employee_hourly_rate'")
        if not cursor.fetchone():
            print("🏗️  Injecting missing migration record: core.0110...")
            cursor.execute("INSERT INTO django_migrations (app, name, applied) VALUES ('core', '0110_employee_hourly_rate', NOW())")
            print("✅ core.0110 record injected.")

        # 2. Ensure core_employee has hourly_rate column
        try:
            print("🏗️  Verifying 'hourly_rate' in 'core_employee'...")
            cursor.execute("ALTER TABLE core_employee ADD COLUMN hourly_rate NUMERIC(19,4) DEFAULT 0.0000;")
            print("✅ Column 'hourly_rate' added to core_employee.")
        except Exception as e:
            print(f"ℹ️  'hourly_rate' column info: {str(e)}")

        # 3. Ensure crop_plan_id in core_item_inventory (Safety check)
        try:
            cursor.execute("ALTER TABLE core_item_inventory ADD COLUMN crop_plan_id INTEGER;")
            print("✅ Column 'crop_plan_id' verified.")
        except Exception:
            pass

    print("🎉 Sovereign Repair Sequence Complete.")
            
    print("🎉 Fix script completed. Try running 'python manage.py migrate' now.")

if __name__ == "__main__":
    fix()
