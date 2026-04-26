
from django.db import migrations, models
from decimal import Decimal

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0120_fix_dailylog_forensic_parity'),
    ]

    operations = [
        # Reconcile ActivityEmployee drift
        # 1. Rename fixed_wage_amount to fixed_wage_cost in DB
        migrations.RunSQL(
            sql="""
            DO $$ 
            BEGIN 
                IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='core_activity_employee' AND column_name='fixed_wage_amount') THEN
                    ALTER TABLE core_activity_employee RENAME COLUMN fixed_wage_amount TO fixed_wage_cost;
                END IF;
            END $$;
            """,
            reverse_sql="ALTER TABLE core_activity_employee RENAME COLUMN fixed_wage_cost TO fixed_wage_amount;"
        ),
        # 2. Add missing columns and ensure nullability/defaults
        migrations.RunSQL(
            sql="""
            -- Ensure columns exist
            ALTER TABLE core_activity_employee 
            ADD COLUMN IF NOT EXISTS is_hourly BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS hourly_rate NUMERIC(19,4) DEFAULT 0,
            ADD COLUMN IF NOT EXISTS achievement_qty NUMERIC(19,4) DEFAULT 0,
            ADD COLUMN IF NOT EXISTS achievement_uom VARCHAR(50) DEFAULT '';
            
            -- Ensure fixed_wage_cost is nullable to match model
            ALTER TABLE core_activity_employee ALTER COLUMN fixed_wage_cost DROP NOT NULL;
            
            -- Handle zombie mandatory column 'pay_mode' only on legacy databases.
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'core_activity_employee'
                      AND column_name = 'pay_mode'
                ) THEN
                    ALTER TABLE core_activity_employee ALTER COLUMN pay_mode DROP NOT NULL;
                END IF;
            END $$;
            """,
            reverse_sql="""
            ALTER TABLE core_activity_employee ALTER COLUMN fixed_wage_cost SET NOT NULL;
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'core_activity_employee'
                      AND column_name = 'pay_mode'
                ) THEN
                    ALTER TABLE core_activity_employee ALTER COLUMN pay_mode SET NOT NULL;
                END IF;
            END $$;
            """
        ),
    ]
