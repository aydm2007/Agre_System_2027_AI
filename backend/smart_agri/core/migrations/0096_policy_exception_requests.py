from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0095_policy_engine_foundation"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PolicyExceptionRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("draft", "Draft"), ("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected"), ("applied", "Applied"), ("expired", "Expired")], default="draft", max_length=20)),
                ("policy_fields", models.JSONField(blank=True, default=list)),
                ("requested_patch", models.JSONField(blank=True, default=dict)),
                ("rationale", models.TextField(blank=True, default="")),
                ("effective_from", models.DateTimeField(default=django.utils.timezone.now)),
                ("effective_to", models.DateTimeField(blank=True, null=True)),
                ("simulate_summary", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("applied_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("farm", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="policy_exception_requests", to="core.farm")),
                ("rejected_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("requested_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "core_policyexceptionrequest",
                "managed": True,
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="policyexceptionrequest",
            index=models.Index(fields=["farm", "status", "effective_from"], name="core_policye_farm_id_a59355_idx"),
        ),
        migrations.CreateModel(
            name="PolicyExceptionEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(choices=[("created", "Created"), ("submitted", "Submitted"), ("approved", "Approved"), ("rejected", "Rejected"), ("applied", "Applied"), ("expired", "Expired")], max_length=20)),
                ("note", models.CharField(blank=True, default="", max_length=255)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("exception_request", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="events", to="core.policyexceptionrequest")),
                ("farm", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="policy_exception_events", to="core.farm")),
            ],
            options={
                "db_table": "core_policyexceptionevent",
                "managed": True,
                "ordering": ["created_at"],
            },
        ),
    ]
