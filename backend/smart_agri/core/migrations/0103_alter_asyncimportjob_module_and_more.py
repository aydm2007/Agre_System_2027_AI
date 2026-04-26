from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0102_asyncreportrequest_export_type_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="asyncimportjob",
            name="module",
            field=models.CharField(
                choices=[("inventory", "Inventory"), ("planning", "Planning")],
                default="inventory",
                max_length=40,
            ),
        ),
        migrations.AlterField(
            model_name="asyncimportjob",
            name="template_code",
            field=models.CharField(
                choices=[
                    ("inventory_count_sheet", "Inventory Count Sheet"),
                    ("inventory_operational_adjustment", "Inventory Operational Adjustment"),
                    ("inventory_opening_balance", "Inventory Opening Balance"),
                    ("inventory_item_master", "Inventory Item Master"),
                    ("planning_master_schedule", "Planning Master Schedule"),
                    ("planning_crop_plan_structure", "Planning Crop Plan Structure"),
                    ("planning_crop_plan_budget", "Planning Crop Plan Budget"),
                ],
                max_length=80,
            ),
        ),
    ]
