from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0028_financialledger_rls_policy"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="financialledger",
            constraint=models.CheckConstraint(
                check=(
                    (models.Q(debit__gt=0) & models.Q(credit=0))
                    | (models.Q(credit__gt=0) & models.Q(debit=0))
                ),
                name="financialledger_debit_credit_xor_new",
            ),
        ),
    ]
