# Generated migration for adding cohort FK to TreeCensusVarianceAlert
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0053_biologicalassetcohort_parent_cohort_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='treecensusvariancealert',
            name='cohort',
            field=models.ForeignKey(
                blank=True,
                help_text='Linked cohort batch — set during resolution to target specific deduction',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='variance_alerts',
                to='core.biologicalassetcohort',
            ),
        ),
    ]
