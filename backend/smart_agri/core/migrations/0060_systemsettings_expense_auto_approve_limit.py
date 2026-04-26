"""
[AGRI-GUARDIAN Axis 8] Add configurable expense auto-approval limit to SystemSettings.

Previously hardcoded as Decimal('5000.00') in FinancialIntegrityService.
Now configurable via the admin panel.
"""
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0059_restore_crop_supported_tasks_m2m'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemsettings',
            name='expense_auto_approve_limit',
            field=models.DecimalField(
                decimal_places=4,
                default=Decimal('5000.0000'),
                help_text='الحد الأقصى للمصروفات التي تُعتمد تلقائياً بدون مراجعة (ر.ي). ما فوقها يحتاج موافقة.',
                max_digits=19,
            ),
        ),
    ]
