from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0030_activity_cost_precision"),
    ]

    operations = [
        migrations.AlterField(
            model_name="activitycostsnapshot",
            name="cost_materials",
            field=models.DecimalField(decimal_places=4, default=Decimal("0.0000"), max_digits=19),
        ),
        migrations.AlterField(
            model_name="activitycostsnapshot",
            name="cost_labor",
            field=models.DecimalField(decimal_places=4, default=Decimal("0.0000"), max_digits=19),
        ),
        migrations.AlterField(
            model_name="activitycostsnapshot",
            name="cost_machinery",
            field=models.DecimalField(decimal_places=4, default=Decimal("0.0000"), max_digits=19),
        ),
        migrations.AlterField(
            model_name="activitycostsnapshot",
            name="cost_overhead",
            field=models.DecimalField(decimal_places=4, default=Decimal("0.0000"), max_digits=19),
        ),
        migrations.AlterField(
            model_name="activitycostsnapshot",
            name="cost_total",
            field=models.DecimalField(decimal_places=4, default=Decimal("0.0000"), max_digits=19),
        ),
    ]
