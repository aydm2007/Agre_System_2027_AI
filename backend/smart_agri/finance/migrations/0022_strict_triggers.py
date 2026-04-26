from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0021_financialledger_exchange_rate_at_moment_and_more'),
    ]

    operations = [
        # 1. Function to prevent updates/deletes (idempotent via CREATE OR REPLACE)
        migrations.RunSQL(
            sql="""
            CREATE OR REPLACE FUNCTION prevent_modification()
            RETURNS TRIGGER AS $$
            BEGIN
                IF (TG_OP = 'DELETE') THEN
                    RAISE EXCEPTION 'Access Denied: Financial Ledger is Immutable (DELETE forbidden).';
                ELSIF (TG_OP = 'UPDATE') THEN
                    RAISE EXCEPTION 'Access Denied: Financial Ledger is Immutable (UPDATE forbidden).';
                END IF;
                RETURN NULL;
            END;
            $$ LANGUAGE plpgsql;
            """,
            reverse_sql="DROP FUNCTION IF EXISTS prevent_modification();"
        ),

        # 2. Trigger for FinancialLedger
        # [AGRI-GUARDIAN] Table uses db_table='core_financialledger' (Safe-Move from core app)
        # Drop first to make idempotent (trigger may exist from earlier migration)
        migrations.RunSQL(
            sql="""
            DROP TRIGGER IF EXISTS trg_financialledger_immutable ON core_financialledger;
            CREATE TRIGGER trg_financialledger_immutable
            BEFORE UPDATE OR DELETE ON core_financialledger
            FOR EACH ROW
            EXECUTE FUNCTION prevent_modification();
            """,
            reverse_sql="DROP TRIGGER IF EXISTS trg_financialledger_immutable ON core_financialledger;"
        ),
    ]
