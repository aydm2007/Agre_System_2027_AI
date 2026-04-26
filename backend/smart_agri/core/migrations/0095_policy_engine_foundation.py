from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0094_farmsettings_self_variance_and_smart_card"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PolicyPackage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, unique=True)),
                ("slug", models.SlugField(max_length=120, unique=True)),
                ("description", models.TextField(blank=True, default="")),
                ("scope", models.CharField(choices=[("sector_central", "Sector Central")], default="sector_central", max_length=40)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "core_policypackage",
                "managed": True,
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="PolicyVersion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("version_label", models.CharField(max_length=40)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("approved", "Approved"), ("retired", "Retired")], default="draft", max_length=20)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("package", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="versions", to="core.policypackage")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "core_policyversion",
                "managed": True,
                "ordering": ["package__name", "-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="policyversion",
            constraint=models.UniqueConstraint(fields=("package", "version_label"), name="uniq_policy_version_per_package"),
        ),
        migrations.CreateModel(
            name="FarmPolicyBinding",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("effective_from", models.DateTimeField(default=django.utils.timezone.now)),
                ("effective_to", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("reason", models.CharField(blank=True, default="", max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("farm", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="policy_bindings", to="core.farm")),
                ("policy_version", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="bindings", to="core.policyversion")),
            ],
            options={
                "db_table": "core_farmpolicybinding",
                "managed": True,
                "ordering": ["-effective_from", "-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="farmpolicybinding",
            index=models.Index(fields=["farm", "is_active", "effective_from"], name="core_farmpo_farm_id_6ebc22_idx"),
        ),
        migrations.CreateModel(
            name="PolicyActivationRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("draft", "Draft"), ("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected"), ("applied", "Applied")], default="draft", max_length=20)),
                ("rationale", models.TextField(blank=True, default="")),
                ("effective_from", models.DateTimeField(default=django.utils.timezone.now)),
                ("simulate_summary", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("applied_binding", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="activation_requests", to="core.farmpolicybinding")),
                ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("farm", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="policy_activation_requests", to="core.farm")),
                ("policy_version", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="activation_requests", to="core.policyversion")),
                ("rejected_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("requested_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "core_policyactivationrequest",
                "managed": True,
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="PolicyActivationEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(choices=[("created", "Created"), ("submitted", "Submitted"), ("approved", "Approved"), ("rejected", "Rejected"), ("applied", "Applied")], max_length=20)),
                ("note", models.CharField(blank=True, default="", max_length=255)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("activation_request", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="events", to="core.policyactivationrequest")),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("farm", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="policy_activation_events", to="core.farm")),
                ("policy_version", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="activation_events", to="core.policyversion")),
            ],
            options={
                "db_table": "core_policyactivationevent",
                "managed": True,
                "ordering": ["created_at"],
            },
        ),
    ]
