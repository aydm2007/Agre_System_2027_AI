from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0019_costconfiguration_overhead_precision"),
    ]

    operations = [
        migrations.AddField(
            model_name="actualexpense",
            name="budget_classification",
            field=models.ForeignKey(
                blank=True,
                help_text="Approved BudgetCode for this expense.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="actual_expenses",
                to="finance.budgetclassification",
            ),
        ),
        migrations.AddField(
            model_name="actualexpense",
            name="replenishment_reference",
            field=models.CharField(
                blank=True,
                help_text="Approved replenishment request reference.",
                max_length=100,
                null=True,
            ),
        ),
    ]
