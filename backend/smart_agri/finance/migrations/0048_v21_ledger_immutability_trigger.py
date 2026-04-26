"""
Migration: Append-Only Ledger PostgreSQL Trigger
[AGRI-GUARDIAN Axis 2 / AGENTS.md §Rule-2]

Defense-in-depth: Even if application-level immutability is bypassed
(e.g. raw SQL, admin shell, bulk_update), the DB trigger will RAISE
an exception blocking UPDATE or DELETE on core_financialledger.
"""
from django.db import migrations

FORWARD_SQL = """
-- [AGRI-GUARDIAN] Append-only enforcement trigger for FinancialLedger.
-- Only INSERT is allowed. UPDATE and DELETE are blocked at DB level.
CREATE OR REPLACE FUNCTION fn_financialledger_immutable()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION
        'SECURITY [Axis-2]: core_financialledger is append-only. '
        'UPDATE/DELETE is forbidden. Use reversal entries.';
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- DROP existing trigger if present (idempotent re-application)
DROP TRIGGER IF EXISTS trg_financialledger_immutable ON core_financialledger;

CREATE TRIGGER trg_financialledger_immutable
    BEFORE UPDATE OR DELETE ON core_financialledger
    FOR EACH ROW
    EXECUTE FUNCTION fn_financialledger_immutable();

-- Comment for documentation
COMMENT ON TRIGGER trg_financialledger_immutable ON core_financialledger IS
    'AGRI-GUARDIAN Axis-2: Ledger immutability. No UPDATE/DELETE allowed.';
"""

REVERSE_SQL = """
DROP TRIGGER IF EXISTS trg_financialledger_immutable ON core_financialledger;
DROP FUNCTION IF EXISTS fn_financialledger_immutable();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0047_v21_approvalstageevent_action_type"),
    ]

    operations = [
        migrations.RunSQL(
            sql=FORWARD_SQL,
            reverse_sql=REVERSE_SQL,
            hints={"model_name": "financialledger"},
        ),
    ]
