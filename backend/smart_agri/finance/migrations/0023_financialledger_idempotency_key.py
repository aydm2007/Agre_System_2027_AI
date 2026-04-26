from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0022_strict_triggers"),
    ]

    operations = [
        migrations.AddField(
            model_name="financialledger",
            name="idempotency_key",
            field=models.CharField(
                max_length=100,
                unique=True,
                null=True,
                blank=True,
                help_text="لمنع تكرار القيد عند ضعف الإشارة V2",
            ),
        ),
    ]
