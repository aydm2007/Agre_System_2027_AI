
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0122_fix_activity_harvest_parity'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='harvestlot',
                    name='status',
                    field=models.CharField(default='draft', max_length=20, verbose_name='حالة الدفعة'),
                ),
                migrations.AddField(
                    model_name='harvestlot',
                    name='is_final',
                    field=models.BooleanField(default=False, verbose_name='نهائي'),
                ),
                migrations.AddField(
                    model_name='harvestlot',
                    name='eternity_proof_id',
                    field=models.UUIDField(blank=True, help_text='Sovereign forensic hash bundle', null=True),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    ALTER TABLE core_harvestlot
                        ADD COLUMN IF NOT EXISTS status varchar(20) NULL DEFAULT 'draft';
                    ALTER TABLE core_harvestlot
                        ADD COLUMN IF NOT EXISTS eternity_proof_id uuid NULL;
                    ALTER TABLE core_harvestlot
                        ALTER COLUMN status DROP NOT NULL;
                    """,
                    reverse_sql="""
                    ALTER TABLE core_harvestlot DROP COLUMN IF EXISTS eternity_proof_id;
                    ALTER TABLE core_harvestlot DROP COLUMN IF EXISTS status;
                    """,
                ),
                migrations.RunSQL(
                    sql="""
                    ALTER TABLE core_harvestlot
                        ADD COLUMN IF NOT EXISTS is_final boolean NULL DEFAULT false;
                    ALTER TABLE core_harvestlot
                        ALTER COLUMN is_final DROP NOT NULL;
                    """,
                    reverse_sql="""
                    ALTER TABLE core_harvestlot DROP COLUMN IF EXISTS is_final;
                    """,
                ),
            ]
        ),
    ]
