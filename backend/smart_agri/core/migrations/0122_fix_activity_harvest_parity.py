
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0121_fix_activity_employee_parity'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='activityharvest',
                    name='is_final_delivery',
                    field=models.BooleanField(default=False, verbose_name='تسليم نهائي'),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    ALTER TABLE core_activity_harvest
                        ADD COLUMN IF NOT EXISTS is_final_delivery boolean NOT NULL DEFAULT false;
                    ALTER TABLE core_activity_harvest
                        ALTER COLUMN is_final_delivery DROP NOT NULL;
                    """,
                    reverse_sql="""
                    ALTER TABLE core_activity_harvest
                        DROP COLUMN IF EXISTS is_final_delivery;
                    """,
                ),
            ]
        ),
    ]
