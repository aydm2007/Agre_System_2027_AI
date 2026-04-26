from django.db import migrations, models
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0015_fiscalperiod_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='costconfiguration',
            name='variance_warning_pct',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('10.00'),
                help_text='حد التحذير للانحراف كنسبة مئوية من الميزانية',
                max_digits=5,
            ),
        ),
        migrations.AddField(
            model_name='costconfiguration',
            name='variance_critical_pct',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('20.00'),
                help_text='حد الانحراف الحرج كنسبة مئوية من الميزانية',
                max_digits=5,
            ),
        ),
    ]
