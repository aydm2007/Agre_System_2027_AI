"""
[AGRI-GUARDIAN §Axis-6] Migration: Add database-level RLS policies for core tables.

Creates PostgreSQL Row-Level Security policies for core tables:
- core_dailylog (has direct farm_id)
- core_activity (accesses farm via log_id -> core_dailylog)

Finance and accounts RLS policies are in their respective app migrations.
"""
from django.db import migrations


FORWARD_SQL = """
-- =============================================================
-- [AGRI-GUARDIAN] Database-Level RLS — Core Tables Only
-- =============================================================

-- 1. DailyLog (core_dailylog) — has direct farm_id
ALTER TABLE core_dailylog ENABLE ROW LEVEL SECURITY;
ALTER TABLE core_dailylog FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS rls_dailylog_farm_isolation ON core_dailylog;
CREATE POLICY rls_dailylog_farm_isolation ON core_dailylog
    USING (
        farm_id IN (
            SELECT farm_id FROM accounts_farmmembership
            WHERE user_id = current_setting('app.user_id', true)::int
        )
    );


-- 2. Activity (core_activity) — accesses farm via log_id -> core_dailylog.farm_id
ALTER TABLE core_activity ENABLE ROW LEVEL SECURITY;
ALTER TABLE core_activity FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS rls_activity_farm_isolation ON core_activity;
CREATE POLICY rls_activity_farm_isolation ON core_activity
    USING (
        log_id IN (
            SELECT dl.id FROM core_dailylog dl
            WHERE dl.farm_id IN (
                SELECT farm_id FROM accounts_farmmembership
                WHERE user_id = current_setting('app.user_id', true)::int
            )
        )
    );
"""

REVERSE_SQL = """
DROP POLICY IF EXISTS rls_activity_farm_isolation ON core_activity;
ALTER TABLE core_activity DISABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS rls_dailylog_farm_isolation ON core_dailylog;
ALTER TABLE core_dailylog DISABLE ROW LEVEL SECURITY;
"""


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0049_roledelegation_rls_policy'),
        ('accounts', '0008_populate_group_permissions'),
    ]

    operations = [
        migrations.RunSQL(sql=FORWARD_SQL, reverse_sql=REVERSE_SQL),
    ]
