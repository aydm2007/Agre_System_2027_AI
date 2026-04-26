from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0090_alter_attachmentlifecycleevent_options_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='IntegrationOutboxEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_id', models.CharField(max_length=64, unique=True)),
                ('event_type', models.CharField(db_index=True, max_length=128)),
                ('aggregate_type', models.CharField(db_index=True, max_length=64)),
                ('aggregate_id', models.CharField(db_index=True, max_length=64)),
                ('destination', models.CharField(default='events', max_length=255)),
                ('payload', models.JSONField(blank=True, default=dict)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('occurred_at', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('dispatched', 'Dispatched'), ('failed', 'Failed'), ('dead_letter', 'Dead letter')], db_index=True, default='pending', max_length=24)),
                ('attempts', models.PositiveIntegerField(default=0)),
                ('max_attempts', models.PositiveIntegerField(default=10)),
                ('available_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('dispatched_at', models.DateTimeField(blank=True, null=True)),
                ('last_error', models.TextField(blank=True, default='')),
                ('locked_at', models.DateTimeField(blank=True, null=True)),
                ('locked_by', models.CharField(blank=True, default='', max_length=128)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('activity', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='integration_outbox_events', to='core.activity')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_integration_outbox_events', to=settings.AUTH_USER_MODEL)),
                ('farm', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='integration_outbox_events', to='core.farm')),
            ],
            options={
                'db_table': 'core_integration_outbox_event',
                'ordering': ['status', 'available_at', 'id'],
            },
        ),
        migrations.AddIndex(
            model_name='integrationoutboxevent',
            index=models.Index(fields=['status', 'available_at'], name='core_integr_status_82a9d0_idx'),
        ),
        migrations.AddIndex(
            model_name='integrationoutboxevent',
            index=models.Index(fields=['event_type', 'status'], name='core_integr_event_t_5b913c_idx'),
        ),
        migrations.AddIndex(
            model_name='integrationoutboxevent',
            index=models.Index(fields=['farm', 'status'], name='core_integr_farm_id_f10203_idx'),
        ),
    ]
