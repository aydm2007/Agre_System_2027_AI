from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0029_financialledger_debit_credit_xor"),
    ]

    operations = [
        migrations.AddField(
            model_name="actualexpense",
            name="status",
            field=models.CharField(db_index=True, default="open", max_length=20),
        ),
    ]

