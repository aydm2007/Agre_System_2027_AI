from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0035_cropplan_budget_precision"),
    ]

    operations = [
        migrations.AddField(
            model_name="dailylog",
            name="fuel_alert_approved_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="dailylog",
            name="fuel_alert_approved_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="daily_logs_fuel_alert_approvals",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="dailylog",
            name="fuel_alert_note",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="dailylog",
            name="fuel_alert_status",
            field=models.CharField(
                choices=[
                    ("OK", "OK"),
                    ("WARNING", "Warning"),
                    ("CRITICAL", "Critical"),
                ],
                db_index=True,
                default="OK",
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="FuelConsumptionAlert",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("machine_hours", models.DecimalField(decimal_places=4, default=0, max_digits=10)),
                ("actual_liters", models.DecimalField(decimal_places=4, max_digits=19)),
                ("expected_liters", models.DecimalField(decimal_places=4, max_digits=19)),
                ("deviation_pct", models.DecimalField(decimal_places=2, max_digits=6)),
                ("status", models.CharField(choices=[("OK", "OK"), ("WARNING", "Warning"), ("CRITICAL", "Critical")], default="OK", max_length=20)),
                ("note", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("asset", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="fuel_alerts", to="core.asset")),
                ("log", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="fuel_alerts", to="core.dailylog")),
            ],
            options={
                "db_table": "core_fuelconsumptionalert",
            },
        ),
        migrations.AddIndex(
            model_name="fuelconsumptionalert",
            index=models.Index(fields=["log"], name="idx_log_fuelalert"),
        ),
        migrations.AddIndex(
            model_name="fuelconsumptionalert",
            index=models.Index(fields=["status"], name="idx_status_fuelalert"),
        ),
    ]
