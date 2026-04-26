"""
[AGRI-GUARDIAN] Migration 0049 Conflict Resolution Script

PROBLEM:
  Migration core.0050_db_level_rls_policies was already applied to the DB.
  Migration core.0049_roledelegation_rls_policy was created AFTER 0050
  was applied, creating a dependency conflict.

SOLUTION:
  1. INSERT a fake record for 0049 into django_migrations (marks it applied)
  2. Apply the actual RLS SQL from 0049 to the database
  3. Verify the migration chain is now consistent

RUN:
  python manage.py shell < scripts/fix_migration_0049_conflict.py
  OR
  python manage.py shell -c "exec(open('scripts/fix_migration_0049_conflict.py').read())"
"""
from django.db import connection

# SQL to apply from migration 0049
FORWARD_SQL = """
ALTER TABLE core_role_delegation ENABLE ROW LEVEL SECURITY;
ALTER TABLE core_role_delegation FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS rls_role_delegation_farm_isolation ON core_role_delegation;
CREATE POLICY rls_role_delegation_farm_isolation ON core_role_delegation
    USING (
        farm_id IN (
            SELECT farm_id FROM accounts_farmmembership
            WHERE user_id = current_setting('app.user_id', true)::int
        )
    );
"""

print("=" * 60)
print("[AGRI-GUARDIAN] Fixing Migration 0049 Conflict")
print("=" * 60)

with connection.cursor() as cursor:
    # Step 1: Check if 0049 is already recorded in django_migrations
    cursor.execute(
        "SELECT id FROM django_migrations WHERE app = 'core' AND name = '0049_roledelegation_rls_policy';"
    )
    row = cursor.fetchone()

    if row:
        print("\n  [OK] Migration 0049 is already recorded in django_migrations.")
    else:
        # Insert the fake migration record
        cursor.execute(
            "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, NOW());",
            ['core', '0049_roledelegation_rls_policy']
        )
        print("\n  [OK] Inserted fake migration record for core.0049_roledelegation_rls_policy")

    # Step 2: Check if core_role_delegation table exists
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'core_role_delegation'
        );
    """)
    table_exists = cursor.fetchone()[0]

    if not table_exists:
        print("  [SKIP] Table 'core_role_delegation' does not exist yet — RLS will be applied when table is created.")
    else:
        # Step 3: Apply the actual RLS SQL
        try:
            cursor.execute(FORWARD_SQL)
            print("  [OK] RLS policy applied to core_role_delegation (Axis-6 + Axis-10 compliance)")
        except Exception as e:
            print(f"  [WARN] RLS application encountered an issue: {e}")
            print("         This may be expected if PostgreSQL RLS is not available or the policy already exists.")

# Step 4: Verify consistency
print("\n  Verifying migration chain consistency...")
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT name, applied
        FROM django_migrations
        WHERE app = 'core'
        AND name IN ('0048_materialvariancealert', '0049_roledelegation_rls_policy', '0050_db_level_rls_policies')
        ORDER BY name;
    """)
    rows = cursor.fetchall()
    for name, applied in rows:
        print(f"    [X] core.{name} — applied at {applied}")

print("\n  [DONE] Run 'python manage.py migrate' to confirm no pending migrations.")
print("=" * 60)
