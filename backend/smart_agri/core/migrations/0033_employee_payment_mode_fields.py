from django.db import migrations, models
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0032_dailylog_observation_data"),
    ]

    operations = [
        migrations.AddField(
            model_name="employee",
            name="payment_mode",
            field=models.CharField(
                choices=[
                    ("OFFICIAL", "Official Salary (Central)"),
                    ("SURRA", "Shift Rate (Surra)"),
                    ("PIECE", "Piece Rate (Muqawala)"),
                ],
                default="SURRA",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="employee",
            name="base_salary",
            field=models.DecimalField(
                decimal_places=4,
                default=Decimal("0.0000"),
                help_text="For Official employees only",
                max_digits=19,
            ),
        ),
        migrations.AddField(
            model_name="employee",
            name="shift_rate",
            field=models.DecimalField(
                decimal_places=4,
                default=Decimal("0.0000"),
                help_text="Daily Surra value for casual labor",
                max_digits=19,
            ),
        ),
        migrations.AddField(
            model_name="employee",
            name="guarantor_name",
            field=models.CharField(
                blank=True,
                help_text="Required for casual labor (Amin/Supervisor)",
                max_length=100,
            ),
        ),
    ]
