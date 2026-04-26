# [AGRI-GUARDIAN] Add old_payload + reason to AuditLog for forensic diff
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0040_expand_rls_coverage'),
    ]

    operations = [
        migrations.AddField(
            model_name='auditlog',
            name='old_payload',
            field=models.JSONField(blank=True, default=dict, help_text='State before mutation for forensic diff'),
        ),
        migrations.AddField(
            model_name='auditlog',
            name='reason',
            field=models.CharField(blank=True, default='', help_text='Mandatory explanation for sensitive changes', max_length=500),
        ),
    ]
