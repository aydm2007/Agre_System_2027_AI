from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0018_alter_costconfiguration_currency"),
    ]

    operations = [
        migrations.AlterField(
            model_name="costconfiguration",
            name="overhead_rate_per_hectare",
            field=models.DecimalField(
                decimal_places=4,
                default=Decimal("50.0000"),
                help_text="معدل تكلفة النفقات العامة لكل هكتار (ريال يمني - دقة عالية)",
                max_digits=19,
            ),
        ),
    ]
