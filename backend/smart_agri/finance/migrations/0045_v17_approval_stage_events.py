from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0044_v12_approval_chain_state"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ApprovalStageEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("stage_number", models.PositiveSmallIntegerField(default=1)),
                ("role", models.CharField(choices=[("MANAGER", "Farm Manager"), ("FARM_FINANCE_MANAGER", "Farm Finance Manager"), ("SECTOR_ACCOUNTANT", "Sector Accountant"), ("SECTOR_REVIEWER", "Sector Reviewer"), ("SECTOR_CHIEF_ACCOUNTANT", "Sector Chief Accountant"), ("FINANCE_DIRECTOR", "Sector Finance Director"), ("SECTOR_DIRECTOR", "Sector Director")], max_length=30)),
                ("action_type", models.CharField(choices=[("CREATED", "Created"), ("STAGE_APPROVED", "Stage Approved"), ("FINAL_APPROVED", "Final Approved"), ("REJECTED", "Rejected"), ("AUTO_ESCALATED", "Auto Escalated")], max_length=24)),
                ("note", models.CharField(blank=True, default="", max_length=500)),
                ("snapshot", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="approval_stage_events", to=settings.AUTH_USER_MODEL)),
                ("request", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="stage_events", to="finance.approvalrequest")),
            ],
            options={
                "db_table": "finance_approvalstageevent",
                "verbose_name": "حدث مرحلة اعتماد",
                "verbose_name_plural": "أحداث مراحل الاعتماد",
                "ordering": ["request_id", "stage_number", "created_at", "id"],
            },
        ),
        migrations.AddIndex(
            model_name="approvalstageevent",
            index=models.Index(fields=["request", "stage_number"], name="finance_app_request_a6d6b4_idx"),
        ),
        migrations.AddIndex(
            model_name="approvalstageevent",
            index=models.Index(fields=["action_type", "created_at"], name="finance_app_action__2e558c_idx"),
        ),
    ]
