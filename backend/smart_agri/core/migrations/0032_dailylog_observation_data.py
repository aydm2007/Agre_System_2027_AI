from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0031_activity_cost_snapshot_precision"),
    ]

    operations = [
        migrations.AddField(
            model_name="dailylog",
            name="observation_data",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
