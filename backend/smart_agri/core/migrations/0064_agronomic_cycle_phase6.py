"""
[AGRI-GUARDIAN Phase 6] Migration: Agronomic Cycle Schema Enhancements.

Adds:
1. CropPlanStatus.SETTLED choice (via model field max_length increase if needed)
2. BiologicalAssetCohort.capitalized_cost (Decimal 19,4) — Axis 11
3. BiologicalAssetCohort.useful_life_years (PositiveInteger, default=25) — Axis 11
4. VarianceAlert.CATEGORY_SCHEDULE_DEVIATION choice

Note: CropPlanStatus and VarianceAlert category changes are handled
at the Python TextChoices/model level. This migration covers the
actual DB column additions for BiologicalAssetCohort.
"""
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0063_hr_phase4_employee_role_textchoices'),
    ]

    operations = [
        # 1. Add capitalized_cost to BiologicalAssetCohort
        migrations.AddField(
            model_name='biologicalassetcohort',
            name='capitalized_cost',
            field=models.DecimalField(
                max_digits=19,
                decimal_places=4,
                default=Decimal('0.0000'),
                help_text='Total capitalized WIP at JUVENILE→PRODUCTIVE transition',
            ),
        ),

        # 2. Add useful_life_years to BiologicalAssetCohort
        migrations.AddField(
            model_name='biologicalassetcohort',
            name='useful_life_years',
            field=models.PositiveIntegerField(
                default=25,
                help_text='Expected useful life in years for amortization calculation',
            ),
        ),

        # 3. Update CropPlan status field to include SETTLED choice
        migrations.AlterField(
            model_name='cropplan',
            name='status',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('draft', 'Draft'),
                    ('active', 'Active'),
                    ('completed', 'Completed'),
                    ('settled', 'Settled (WIP Closed)'),
                    ('archived', 'Archived'),
                ],
                default='active',
            ),
        ),

        # 4. Update VarianceAlert category field to include SCHEDULE_DEVIATION
        migrations.AlterField(
            model_name='variancealert',
            name='category',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('BUDGET_OVERRUN', 'تجاوز الميزانية'),
                    ('DIESEL_ANOMALY', 'شبهة تلاعب بالديزل'),
                    ('LABOR_EXCESS', 'إسراف في العمالة'),
                    ('MATERIAL_WASTE', 'هدر مواد'),
                    ('SCHEDULE_DEVIATION', 'انحراف عن الجدول الزمني'),
                    ('OTHER', 'أخرى'),
                ],
                default='BUDGET_OVERRUN',
                db_index=True,
            ),
        ),
    ]
