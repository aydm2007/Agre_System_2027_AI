from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0015_fuellog_supervisor_reading_date"),
    ]

    operations = [
        migrations.AddField(
            model_name="fuellog",
            name="measurement_method",
            field=models.CharField(
                choices=[
                    ("DIPSTICK", "Manual Dipstick (Sikh)"),
                    ("COUNTER", "Mechanical Counter"),
                ],
                default="DIPSTICK",
                max_length=20,
            ),
        ),
    ]
