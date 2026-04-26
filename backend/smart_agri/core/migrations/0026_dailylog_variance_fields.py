from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0025_idempotencyrecord_response_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='dailylog',
            name='variance_status',
            field=models.CharField(
                choices=[('OK', 'OK'), ('WARNING', 'WARNING'), ('CRITICAL', 'CRITICAL')],
                db_index=True,
                default='OK',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='dailylog',
            name='variance_note',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='dailylog',
            name='variance_approved_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='daily_logs_variance_approved',
                to='auth.user',
            ),
        ),
        migrations.AddField(
            model_name='dailylog',
            name='variance_approved_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
