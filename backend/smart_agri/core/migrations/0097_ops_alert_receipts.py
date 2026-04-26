from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0096_policy_exception_requests"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="OpsAlertReceipt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fingerprint", models.CharField(db_index=True, max_length=255)),
                ("status", models.CharField(choices=[("acknowledged", "Acknowledged"), ("snoozed", "Snoozed")], max_length=20)),
                ("snooze_until", models.DateTimeField(blank=True, null=True)),
                ("note", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("actor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ops_alert_receipts", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "core_ops_alert_receipt",
                "managed": True,
                "ordering": ["-updated_at"],
            },
        ),
        migrations.AddIndex(
            model_name="opsalertreceipt",
            index=models.Index(fields=["actor", "status"], name="core_opsalert_actor_status_idx"),
        ),
        migrations.AddIndex(
            model_name="opsalertreceipt",
            index=models.Index(fields=["actor", "snooze_until"], name="core_opsalert_actor_snooze_idx"),
        ),
        migrations.AddConstraint(
            model_name="opsalertreceipt",
            constraint=models.UniqueConstraint(fields=("fingerprint", "actor"), name="core_opsalertreceipt_actor_fingerprint_uniq"),
        ),
    ]
