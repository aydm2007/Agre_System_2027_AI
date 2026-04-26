from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0034_farm_zakat_rule"),
    ]

    operations = [
        migrations.AlterField(
            model_name="cropplan",
            name="budget_materials",
            field=models.DecimalField(decimal_places=4, default=Decimal("0.0000"), max_digits=19),
        ),
        migrations.AlterField(
            model_name="cropplan",
            name="budget_labor",
            field=models.DecimalField(decimal_places=4, default=Decimal("0.0000"), max_digits=19),
        ),
        migrations.AlterField(
            model_name="cropplan",
            name="budget_machinery",
            field=models.DecimalField(decimal_places=4, default=Decimal("0.0000"), max_digits=19),
        ),
        migrations.AlterField(
            model_name="cropplan",
            name="budget_total",
            field=models.DecimalField(decimal_places=4, default=Decimal("0.0000"), max_digits=19),
        ),
        migrations.AlterField(
            model_name="cropplan",
            name="budget_amount",
            field=models.DecimalField(decimal_places=4, default=Decimal("0.0000"), max_digits=19),
        ),
        migrations.AlterField(
            model_name="cropplanbudgetline",
            name="rate_budget",
            field=models.DecimalField(decimal_places=4, default=Decimal("0.0000"), max_digits=19),
        ),
        migrations.AlterField(
            model_name="cropplanbudgetline",
            name="total_budget",
            field=models.DecimalField(decimal_places=4, default=Decimal("0.0000"), max_digits=19),
        ),
    ]
