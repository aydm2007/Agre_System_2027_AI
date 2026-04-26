"""
[AGRI-GUARDIAN Axis-6 & Axis-10] Migration 0049: RoleDelegation RLS Policy

This migration applies Row-Level Security for delegation records using a
schema-aware strategy:
- Prefer accounts_roledelegation (current production table).
- Fallback to core_role_delegation (legacy table, if present).

It is defensive to avoid bootstrapping failures on fresh test databases.
"""
from django.db import migrations


FORWARD_SQL = """
-- =============================================================
-- [AGRI-GUARDIAN Axis-6 + Axis-10] Defensive RLS for role delegation
-- =============================================================
DO $$
DECLARE
    target_table text;
BEGIN
    IF to_regclass('public.accounts_roledelegation') IS NOT NULL THEN
        target_table := 'accounts_roledelegation';
    ELSIF to_regclass('public.core_role_delegation') IS NOT NULL THEN
        target_table := 'core_role_delegation';
    ELSE
        -- No delegation table in current schema state.
        RETURN;
    END IF;

    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', target_table);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', target_table);
    EXECUTE format('DROP POLICY IF EXISTS rls_role_delegation_farm_isolation ON %I', target_table);

    EXECUTE format(
        'CREATE POLICY rls_role_delegation_farm_isolation ON %I
         USING (
            farm_id IN (
                SELECT farm_id FROM accounts_farmmembership
                WHERE user_id = current_setting(''app.user_id'', true)::int
            )
         )',
        target_table
    );
END $$;
"""


REVERSE_SQL = """
DO $$
DECLARE
    target_table text;
BEGIN
    IF to_regclass('public.accounts_roledelegation') IS NOT NULL THEN
        target_table := 'accounts_roledelegation';
    ELSIF to_regclass('public.core_role_delegation') IS NOT NULL THEN
        target_table := 'core_role_delegation';
    ELSE
        RETURN;
    END IF;

    EXECUTE format('DROP POLICY IF EXISTS rls_role_delegation_farm_isolation ON %I', target_table);
    EXECUTE format('ALTER TABLE %I DISABLE ROW LEVEL SECURITY', target_table);
END $$;
"""


class Migration(migrations.Migration):
    """
    [AGRI-GUARDIAN Axis-6 + Axis-10] RLS gap fix.
    Applies delegation RLS policy on the active delegation table.
    """

    dependencies = [
        ('core', '0048_materialvariancealert'),
        ('accounts', '0008_populate_group_permissions'),
    ]

    operations = [
        migrations.RunSQL(sql=FORWARD_SQL, reverse_sql=REVERSE_SQL),
    ]
