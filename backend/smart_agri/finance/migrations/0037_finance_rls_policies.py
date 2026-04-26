"""
[AGRI-GUARDIAN §Axis-6] RLS policies for finance tables.
"""
from django.db import migrations


FORWARD_SQL = """
-- FinancialLedger — farm_id is nullable
ALTER TABLE core_financialledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE core_financialledger FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS rls_ledger_farm_isolation ON core_financialledger;
CREATE POLICY rls_ledger_farm_isolation ON core_financialledger
    USING (
        farm_id IS NULL
        OR farm_id IN (
            SELECT farm_id FROM accounts_farmmembership
            WHERE user_id = current_setting('app.user_id', true)::int
        )
    );

-- TreasuryTransaction — direct farm_id
ALTER TABLE core_treasurytransaction ENABLE ROW LEVEL SECURITY;
ALTER TABLE core_treasurytransaction FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS rls_treasury_farm_isolation ON core_treasurytransaction;
CREATE POLICY rls_treasury_farm_isolation ON core_treasurytransaction
    USING (
        farm_id IN (
            SELECT farm_id FROM accounts_farmmembership
            WHERE user_id = current_setting('app.user_id', true)::int
        )
    );
"""

REVERSE_SQL = """
DROP POLICY IF EXISTS rls_treasury_farm_isolation ON core_treasurytransaction;
ALTER TABLE core_treasurytransaction DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS rls_ledger_farm_isolation ON core_financialledger;
ALTER TABLE core_financialledger DISABLE ROW LEVEL SECURITY;
"""


class Migration(migrations.Migration):
    dependencies = [
        ('finance', '0036_approvalrequest_cost_center_approvalrule_cost_center_and_more'),
        ('accounts', '0008_populate_group_permissions'),
    ]
    operations = [
        migrations.RunSQL(sql=FORWARD_SQL, reverse_sql=REVERSE_SQL),
    ]
