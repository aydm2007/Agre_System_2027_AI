from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0085_v11_governance_and_attachment_policy"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='attachment',
            name='storage_tier',
            field=models.CharField(choices=[('hot', 'Hot'), ('archive', 'Archive')], default='hot', max_length=16),
        ),
        migrations.AddField(
            model_name='attachment',
            name='malware_scan_status',
            field=models.CharField(choices=[('pending', 'Pending'), ('passed', 'Passed'), ('quarantined', 'Quarantined')], default='pending', max_length=20),
        ),
        migrations.AddField(
            model_name='attachment',
            name='quarantine_reason',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.CreateModel(
            name='RemoteReviewLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reviewed_at', models.DateTimeField(auto_now_add=True)),
                ('review_type', models.CharField(choices=[('weekly', 'مراجعة أسبوعية'), ('exception', 'مراجعة استثنائية')], default='weekly', max_length=20)),
                ('notes', models.TextField(blank=True, default='')),
                ('exceptions_found', models.PositiveIntegerField(default=0)),
                ('farm', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='remote_review_logs', to='core.farm')),
                ('reviewed_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='remote_reviews', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'core_remotereviewlog',
                'verbose_name': 'سجل المراجعة القطاعية عن بعد',
                'verbose_name_plural': 'سجلات المراجعة القطاعية عن بعد',
                'ordering': ['-reviewed_at'],
            },
        ),
    ]
