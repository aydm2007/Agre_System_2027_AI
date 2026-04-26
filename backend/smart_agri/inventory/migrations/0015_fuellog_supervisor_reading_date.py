from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0033_employee_payment_mode_fields'),
        ('inventory', '0014_tankcalibration_fuellog'),
    ]

    operations = [
        migrations.AddField(
            model_name='fuellog',
            name='reading_date',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='fuellog',
            name='supervisor',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='fuel_logs',
                to='core.supervisor',
            ),
        ),
    ]
