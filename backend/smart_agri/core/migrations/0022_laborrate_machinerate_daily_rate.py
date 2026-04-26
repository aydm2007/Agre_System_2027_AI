from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0021_activity_deleted_at_activity_deleted_by_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="laborrate",
            name="daily_rate",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=12,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="machinerate",
            name="daily_rate",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=12,
                null=True,
            ),
        ),
    ]
