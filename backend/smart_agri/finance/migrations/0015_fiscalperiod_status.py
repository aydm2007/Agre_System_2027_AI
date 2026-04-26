from django.db import migrations, models


def set_fiscal_period_status(apps, schema_editor):
    FiscalPeriod = apps.get_model('finance', 'FiscalPeriod')
    FiscalPeriod.objects.filter(is_closed=True).update(status='hard_closed')
    FiscalPeriod.objects.filter(is_closed=False).update(status='open')


def unset_fiscal_period_status(apps, schema_editor):
    FiscalPeriod = apps.get_model('finance', 'FiscalPeriod')
    FiscalPeriod.objects.filter(status='hard_closed').update(is_closed=True)
    FiscalPeriod.objects.exclude(status='hard_closed').update(is_closed=False)


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0014_budgetclassification_sectorrelationship'),
    ]

    operations = [
        migrations.AddField(
            model_name='fiscalperiod',
            name='status',
            field=models.CharField(choices=[('open', 'Open'), ('soft_closed', 'Soft Closed'), ('hard_closed', 'Hard Closed')], default='open', max_length=20),
        ),
        migrations.RunPython(set_fiscal_period_status, unset_fiscal_period_status),
    ]
