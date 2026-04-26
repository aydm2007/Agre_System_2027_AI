from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0017_alter_financialledger_account_code"),
    ]

    operations = [
        migrations.AlterField(
            model_name="costconfiguration",
            name="currency",
            field=models.CharField(
                choices=[("YER", "Yemeni Rial"), ("SAR", "Saudi Riyal")],
                default="YER",
                max_length=3,
            ),
        ),
    ]
