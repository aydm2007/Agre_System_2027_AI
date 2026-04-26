from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0043_v11_approval_role_expansion"),
    ]

    operations = [
        migrations.AddField(
            model_name="approvalrequest",
            name="final_required_role",
            field=models.CharField(choices=[("MANAGER", "Farm Manager"), ("FARM_FINANCE_MANAGER", "Farm Finance Manager"), ("SECTOR_ACCOUNTANT", "Sector Accountant"), ("SECTOR_REVIEWER", "Sector Reviewer"), ("SECTOR_CHIEF_ACCOUNTANT", "Sector Chief Accountant"), ("FINANCE_DIRECTOR", "Sector Finance Director"), ("SECTOR_DIRECTOR", "Sector Director")], default="MANAGER", max_length=30, help_text="الدور النهائي المطلوب لاعتماد الطلب بالكامل."),
        ),
        migrations.AddField(
            model_name="approvalrequest",
            name="current_stage",
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="approvalrequest",
            name="total_stages",
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="approvalrequest",
            name="approval_history",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
