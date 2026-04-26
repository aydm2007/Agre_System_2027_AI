import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from django.db import connection

queries = [
    "ALTER TABLE core_activityemployee ADD COLUMN IF NOT EXISTS fixed_wage_cost numeric(19, 4) NULL;",
    "ALTER TABLE core_croptemplatetask ADD COLUMN IF NOT EXISTS days_offset integer DEFAULT 0 NOT NULL;",
    "ALTER TABLE core_croptemplatetask ADD COLUMN IF NOT EXISTS duration_days integer DEFAULT 1 NOT NULL;",
    "ALTER TABLE core_farmsettings ADD COLUMN IF NOT EXISTS enable_timed_plan_compliance boolean DEFAULT false NOT NULL;",
    "ALTER TABLE core_plannedactivity ADD COLUMN IF NOT EXISTS expected_date_end date NULL;",
    "ALTER TABLE core_plannedactivity ADD COLUMN IF NOT EXISTS expected_date_start date NULL;",
    # Add any missing from 0124 just in case they are missing too
    "ALTER TABLE core_farmsettings ADD COLUMN IF NOT EXISTS enabled_modules jsonb DEFAULT '{}'::jsonb NOT NULL;",
    "ALTER TABLE core_farmsettings ADD COLUMN IF NOT EXISTS is_rukun_locked boolean DEFAULT false NOT NULL;",
    "ALTER TABLE core_farmsettings ADD COLUMN IF NOT EXISTS is_smart boolean DEFAULT false NOT NULL;",
    "ALTER TABLE core_farm ADD COLUMN IF NOT EXISTS is_organization boolean DEFAULT false NOT NULL;",
    "ALTER TABLE core_farm ADD COLUMN IF NOT EXISTS operational_mode varchar(50) DEFAULT 'SIMPLE' NOT NULL;",
    "ALTER TABLE core_farm ADD COLUMN IF NOT EXISTS organization_id integer NULL;",
    "ALTER TABLE core_farm ADD COLUMN IF NOT EXISTS parent_id integer NULL;",
    "ALTER TABLE core_farm ADD COLUMN IF NOT EXISTS sensing_mode varchar(50) DEFAULT 'MANUAL' NOT NULL;",
    "ALTER TABLE core_auditlog ADD COLUMN IF NOT EXISTS signature varchar(512) NULL;"
]

try:
    with connection.cursor() as cursor:
        for q in queries:
            try:
                cursor.execute(q)
                print("Executed:", q)
            except Exception as loop_err:
                print("Failed to execute inside loop:", q, "Error:", loop_err)
        connection.commit()
    print('All fixes applied!')
except Exception as e:
    print('Critical Error:', e)
