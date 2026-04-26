
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0119_remove_zombie_tables'),
    ]

    operations = [
        # Reconcile DailyLog forensic fields
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='dailylog',
                    name='sovereign_signature',
                    field=models.CharField(blank=True, help_text='Cryptographic chain signature', max_length=512, null=True),
                ),
                migrations.AddField(
                    model_name='dailylog',
                    name='eternity_proof_id',
                    field=models.UUIDField(blank=True, help_text='Permanent forensic evidence bundle ID', null=True),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    ALTER TABLE core_dailylog
                        ADD COLUMN IF NOT EXISTS sovereign_signature varchar(512) NULL;
                    ALTER TABLE core_dailylog
                        ADD COLUMN IF NOT EXISTS eternity_proof_id uuid NULL;
                    ALTER TABLE core_dailylog
                        ALTER COLUMN sovereign_signature DROP NOT NULL;
                    """,
                    reverse_sql="""
                    ALTER TABLE core_dailylog DROP COLUMN IF EXISTS eternity_proof_id;
                    ALTER TABLE core_dailylog DROP COLUMN IF EXISTS sovereign_signature;
                    """,
                ),
            ]
        ),
        # Reconcile AuditLog parity (Axis 20 Forensic Compliance)
        migrations.RunSQL(
            sql="""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'core_auditlog'
                      AND column_name = 'signature'
                ) THEN
                    ALTER TABLE core_auditlog ALTER COLUMN signature DROP NOT NULL;
                END IF;
            END $$;
            """,
            reverse_sql="""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'core_auditlog'
                      AND column_name = 'signature'
                ) THEN
                    ALTER TABLE core_auditlog ALTER COLUMN signature SET NOT NULL;
                END IF;
            END $$;
            """,
        ),
    ]
