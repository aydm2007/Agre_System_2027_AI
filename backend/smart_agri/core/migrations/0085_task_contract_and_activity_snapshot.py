from django.db import migrations, models


def seed_task_contracts(apps, schema_editor):
    Task = apps.get_model("core", "Task")
    for task in Task.objects.all():
        if not getattr(task, "task_contract", None):
            task.task_contract = {}
        if not getattr(task, "task_contract_version", None):
            task.task_contract_version = 1
        task.save(update_fields=["task_contract", "task_contract_version"])


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0084_farmsettings_governance_policy_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="archetype",
            field=models.CharField(
                choices=[
                    ("GENERAL", "General"),
                    ("IRRIGATION", "Irrigation"),
                    ("MACHINERY", "Machinery"),
                    ("HARVEST", "Harvest"),
                    ("PERENNIAL_SERVICE", "Perennial Service"),
                    ("LABOR_INTENSIVE", "Labor Intensive"),
                    ("MATERIAL_INTENSIVE", "Material Intensive"),
                    ("FUEL_SENSITIVE", "Fuel Sensitive"),
                    ("BIOLOGICAL_ADJUSTMENT", "Biological Adjustment"),
                    ("CONTRACT_SETTLEMENT_LINKED", "Contract Settlement Linked"),
                ],
                default="GENERAL",
                max_length=40,
            ),
        ),
        migrations.AddField(
            model_name="task",
            name="task_contract",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="task",
            name="task_contract_version",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="activity",
            name="task_contract_snapshot",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="activity",
            name="task_contract_version",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.RunPython(seed_task_contracts, migrations.RunPython.noop),
    ]
