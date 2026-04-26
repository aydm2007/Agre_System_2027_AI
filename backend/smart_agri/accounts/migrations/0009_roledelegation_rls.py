"""
[AGRI-GUARDIAN §Axis-6] RLS policy for accounts_roledelegation.
"""
from django.db import migrations


FORWARD_SQL = """
ALTER TABLE accounts_roledelegation ENABLE ROW LEVEL SECURITY;
ALTER TABLE accounts_roledelegation FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS rls_delegation_farm_isolation ON accounts_roledelegation;
CREATE POLICY rls_delegation_farm_isolation ON accounts_roledelegation
    USING (
        farm_id IN (
            SELECT farm_id FROM accounts_farmmembership
            WHERE user_id = current_setting('app.user_id', true)::int
        )
    );
"""

REVERSE_SQL = """
DROP POLICY IF EXISTS rls_delegation_farm_isolation ON accounts_roledelegation;
ALTER TABLE accounts_roledelegation DISABLE ROW LEVEL SECURITY;
"""


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0008_populate_group_permissions'),
    ]
    operations = [
        migrations.RunSQL(sql=FORWARD_SQL, reverse_sql=REVERSE_SQL),
    ]
