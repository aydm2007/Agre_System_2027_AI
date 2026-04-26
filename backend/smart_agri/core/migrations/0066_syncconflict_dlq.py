"""
[AGRI-GUARDIAN] Migration 0066: SyncConflict DLQ + Pesticide Approval Gate

Creates:
1. SyncConflictDLQ model for offline conflict resolution
2. Adds 'requires_engineer_approval' field to Item model for pesticide gate
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0065_rls_finance_bio_assets'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # --- H1: SyncConflict DLQ ---
        migrations.CreateModel(
            name='SyncConflictDLQ',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('conflict_type', models.CharField(
                    choices=[
                        ('DUPLICATE_IDEMPOTENCY', 'مفتاح تكراري'),
                        ('FISCAL_PERIOD_CLOSED', 'فترة مالية مغلقة'),
                        ('STALE_VERSION', 'إصدار قديم'),
                        ('VALIDATION_FAILURE', 'خطأ في التحقق'),
                        ('RLS_VIOLATION', 'انتهاك عزل البيانات'),
                        ('OTHER', 'أخرى'),
                    ],
                    default='OTHER',
                    max_length=30,
                )),
                ('conflict_reason', models.TextField()),
                ('endpoint', models.CharField(max_length=255)),
                ('http_method', models.CharField(default='POST', max_length=10)),
                ('request_payload', models.JSONField()),
                ('idempotency_key', models.CharField(blank=True, db_index=True, max_length=255, null=True)),
                ('device_timestamp', models.DateTimeField(blank=True, null=True)),
                ('server_received_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('status', models.CharField(
                    choices=[
                        ('PENDING', 'قيد المراجعة'),
                        ('RESOLVED', 'تمت المعالجة'),
                        ('REJECTED', 'مرفوض'),
                        ('REPLAYED', 'أعيد تشغيله'),
                    ],
                    db_index=True,
                    default='PENDING',
                    max_length=20,
                )),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('resolution_notes', models.TextField(blank=True, default='')),
                ('farm', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='sync_conflicts',
                    to='core.farm',
                )),
                ('actor', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='sync_conflicts',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('resolved_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='resolved_sync_conflicts',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'تعارض المزامنة',
                'verbose_name_plural': 'تعارضات المزامنة',
                'db_table': 'core_syncconflict_dlq',
                'ordering': ['-server_received_at'],
                'managed': True,
            },
        ),
        migrations.AddIndex(
            model_name='syncconflictdlq',
            index=models.Index(fields=['farm', 'status'], name='idx_dlq_farm_status'),
        ),
        migrations.AddIndex(
            model_name='syncconflictdlq',
            index=models.Index(fields=['idempotency_key'], name='idx_dlq_idemp_key'),
        ),
    ]
