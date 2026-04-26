from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0080_schema_parity_farmsettings_auditlog"),
    ]

    operations = [
        migrations.AlterField(
            model_name="asyncreportrequest",
            name="report_type",
            field=models.CharField(
                choices=[
                    ("profitability", "Profitability"),
                    ("advanced", "Advanced Overview"),
                    ("commercial_pdf", "Commercial PDF"),
                ],
                max_length=60,
            ),
        ),
    ]
