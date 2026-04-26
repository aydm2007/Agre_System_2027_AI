from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0027_activityemployee_surra_units_timesheet_surra_units_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="employmentcontract",
            name="overtime_shift_value",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="قيمة الوردية الإضافية (قيمة الصرة الإضافية) - ريال يمني",
                max_digits=10,
            ),
        ),
        migrations.RemoveField(
            model_name="employmentcontract",
            name="overtime_rate",
        ),
        migrations.RemoveField(
            model_name="activity",
            name="machine",
        ),
    ]
