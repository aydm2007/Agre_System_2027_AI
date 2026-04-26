from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0026_dailylog_variance_fields'),
        ('inventory', '0013_item_deleted_at_item_deleted_by_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='TankCalibration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cm_reading', models.DecimalField(decimal_places=2, max_digits=6, help_text='Reading in CM')),
                ('liters_volume', models.DecimalField(decimal_places=4, max_digits=19, help_text='Equivalent Liters')),
                ('asset', models.ForeignKey(
                    limit_choices_to={'asset_type': 'tank'},
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='calibrations',
                    to='core.asset',
                )),
            ],
            options={
                'db_table': 'inventory_tankcalibration',
                'ordering': ['asset', 'cm_reading'],
                'unique_together': {('asset', 'cm_reading')},
            },
        ),
        migrations.CreateModel(
            name='FuelLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reading_start_cm', models.DecimalField(decimal_places=2, max_digits=6)),
                ('reading_end_cm', models.DecimalField(decimal_places=2, max_digits=6)),
                ('liters_consumed', models.DecimalField(decimal_places=4, editable=False, max_digits=19)),
                ('asset_tank', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.asset')),
                ('farm', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.farm')),
            ],
            options={
                'db_table': 'inventory_fuellog',
                'indexes': [models.Index(fields=['farm', 'asset_tank'], name='inventory_fuellog_farm_asset_tank_idx')],
            },
        ),
    ]
