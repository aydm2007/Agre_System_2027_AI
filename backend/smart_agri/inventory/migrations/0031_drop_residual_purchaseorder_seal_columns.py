from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0030_ensure_purchaseorder_signature_columns"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE inventory_purchaseorder
              DROP COLUMN IF EXISTS technical_seal,
              DROP COLUMN IF EXISTS financial_seal,
              DROP COLUMN IF EXISTS director_seal;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
