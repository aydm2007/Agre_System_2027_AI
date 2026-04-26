import os

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
import django
django.setup()

from django.db import connection

sql_commands = """
ALTER TABLE "core_task" ADD COLUMN IF NOT EXISTS "archetype" varchar(40) DEFAULT 'GENERAL' NOT NULL;
ALTER TABLE "core_task" ALTER COLUMN "archetype" DROP DEFAULT;

ALTER TABLE "core_task" ADD COLUMN IF NOT EXISTS "task_contract" jsonb DEFAULT '{}' NOT NULL;
ALTER TABLE "core_task" ALTER COLUMN "task_contract" DROP DEFAULT;

ALTER TABLE "core_task" ADD COLUMN IF NOT EXISTS "task_contract_version" integer DEFAULT 1 NOT NULL CHECK ("task_contract_version" >= 0);
ALTER TABLE "core_task" ALTER COLUMN "task_contract_version" DROP DEFAULT;

ALTER TABLE "core_activity" ADD COLUMN IF NOT EXISTS "task_contract_snapshot" jsonb DEFAULT '{}' NOT NULL;
ALTER TABLE "core_activity" ALTER COLUMN "task_contract_snapshot" DROP DEFAULT;

ALTER TABLE "core_activity" ADD COLUMN IF NOT EXISTS "task_contract_version" integer DEFAULT 1 NOT NULL CHECK ("task_contract_version" >= 0);
ALTER TABLE "core_activity" ALTER COLUMN "task_contract_version" DROP DEFAULT;
"""

try:
    with connection.cursor() as cursor:
        for stmt in sql_commands.strip().split(';'):
            if stmt.strip():
                try:
                    cursor.execute(stmt)
                    print(f"Executed: {stmt.strip()[:60]}...")
                except Exception as inner_e:
                    # ignore already exists errors or similar
                    print(f"Skipped/Failed {stmt.strip()[:30]}: {inner_e}")
    print("SQL execution complete!")
except Exception as e:
    print(f"Fatal error: {e}")
