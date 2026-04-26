from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0086_v12_attachment_runtime_and_remote_review"),
    ]

    operations = [
        migrations.AddField(
            model_name="attachment",
            name="archive_backend",
            field=models.CharField(blank=True, default="filesystem", max_length=24),
        ),
        migrations.AddField(
            model_name="attachment",
            name="archive_key",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="attachment",
            name="quarantined_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="attachment",
            name="restored_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="attachment",
            name="scanned_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
