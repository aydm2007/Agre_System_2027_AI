from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0124_auditlog_signature_farm_is_organization_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                DROP TABLE IF EXISTS system_logs CASCADE;
                DROP TABLE IF EXISTS audit_logs CASCADE;
                DROP TABLE IF EXISTS users CASCADE;
                DROP TABLE IF EXISTS workflow_state CASCADE;
            """,
            reverse_sql="-- no reverse for residual zombie cleanup",
        )
    ]
