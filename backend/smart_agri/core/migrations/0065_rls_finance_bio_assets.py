"""
[AGRI-GUARDIAN §Axis-6] Migration: RLS for Financial Ledger and Biological Assets.

Extends database-level Row-Level Security to agronomic/financial tables:
1. finance_financialledger (has direct farm_id)
2. core_biologicalassetcohort (has direct farm_id)

Uses the same pattern as 0050_db_level_rls_policies:
  - current_setting('app.user_id', true) for session-scoped user identity
  - accounts_farmmembership for farm access resolution
"""
from django.db import migrations


FORWARD_SQL = """
-- =============================================================
-- [AGRI-GUARDIAN §Axis-6] Database-Level RLS — Finance & Bio Assets
-- =============================================================

-- 1. FinancialLedger (finance_financialledger) — has direct farm_id
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'finance_financialledger'
    ) THEN
        EXECUTE 'ALTER TABLE finance_financialledger ENABLE ROW LEVEL SECURITY';
        EXECUTE 'ALTER TABLE finance_financialledger FORCE ROW LEVEL SECURITY';

        EXECUTE 'DROP POLICY IF EXISTS rls_ledger_farm_isolation ON finance_financialledger';
        EXECUTE '
            CREATE POLICY rls_ledger_farm_isolation ON finance_financialledger
            USING (
                farm_id IN (
                    SELECT farm_id FROM accounts_farmmembership
                    WHERE user_id = current_setting(''app.user_id'', true)::int
                )
            )
        ';
    END IF;
END $$;


-- 2. BiologicalAssetCohort (core_biologicalassetcohort) — has direct farm_id
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'core_biologicalassetcohort'
    ) THEN
        EXECUTE 'ALTER TABLE core_biologicalassetcohort ENABLE ROW LEVEL SECURITY';
        EXECUTE 'ALTER TABLE core_biologicalassetcohort FORCE ROW LEVEL SECURITY';

        EXECUTE 'DROP POLICY IF EXISTS rls_bio_cohort_farm_isolation ON core_biologicalassetcohort';
        EXECUTE '
            CREATE POLICY rls_bio_cohort_farm_isolation ON core_biologicalassetcohort
            USING (
                farm_id IN (
                    SELECT farm_id FROM accounts_farmmembership
                    WHERE user_id = current_setting(''app.user_id'', true)::int
                )
            )
        ';
    END IF;
END $$;


-- 3. VarianceAlert (core_variancealert) — has direct farm_id
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'core_variancealert'
    ) THEN
        EXECUTE 'ALTER TABLE core_variancealert ENABLE ROW LEVEL SECURITY';
        EXECUTE 'ALTER TABLE core_variancealert FORCE ROW LEVEL SECURITY';

        EXECUTE 'DROP POLICY IF EXISTS rls_variance_alert_farm_isolation ON core_variancealert';
        EXECUTE '
            CREATE POLICY rls_variance_alert_farm_isolation ON core_variancealert
            USING (
                farm_id IN (
                    SELECT farm_id FROM accounts_farmmembership
                    WHERE user_id = current_setting(''app.user_id'', true)::int
                )
            )
        ';
    END IF;
END $$;
"""

REVERSE_SQL = """
DROP POLICY IF EXISTS rls_variance_alert_farm_isolation ON core_variancealert;
ALTER TABLE core_variancealert DISABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS rls_bio_cohort_farm_isolation ON core_biologicalassetcohort;
ALTER TABLE core_biologicalassetcohort DISABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS rls_ledger_farm_isolation ON finance_financialledger;
ALTER TABLE finance_financialledger DISABLE ROW LEVEL SECURITY;
"""


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0064_agronomic_cycle_phase6'),
        ('accounts', '0008_populate_group_permissions'),
    ]

    operations = [
        migrations.RunSQL(sql=FORWARD_SQL, reverse_sql=REVERSE_SQL),
    ]
