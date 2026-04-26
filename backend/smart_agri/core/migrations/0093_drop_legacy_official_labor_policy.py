from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0092_v21_attachment_policy_metadata"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE core_farmsettings
            DROP COLUMN IF EXISTS official_labor_policy;
            """,
            reverse_sql="""
            ALTER TABLE core_farmsettings
            ADD COLUMN IF NOT EXISTS official_labor_policy varchar(24) NOT NULL DEFAULT 'attendance_only';
            ALTER TABLE core_farmsettings
            ALTER COLUMN official_labor_policy DROP DEFAULT;
            """,
        ),
    ]
