from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0042_alter_financialledger_account_code_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="approvalrule",
            name="required_role",
            field=models.CharField(choices=[("MANAGER", "Farm Manager"), ("FARM_FINANCE_MANAGER", "Farm Finance Manager"), ("SECTOR_ACCOUNTANT", "Sector Accountant"), ("SECTOR_REVIEWER", "Sector Reviewer"), ("SECTOR_CHIEF_ACCOUNTANT", "Sector Chief Accountant"), ("FINANCE_DIRECTOR", "Sector Finance Director"), ("SECTOR_DIRECTOR", "Sector Director")], default="MANAGER", max_length=30),
        ),
        migrations.AlterField(
            model_name="approvalrequest",
            name="required_role",
            field=models.CharField(choices=[("MANAGER", "Farm Manager"), ("FARM_FINANCE_MANAGER", "Farm Finance Manager"), ("SECTOR_ACCOUNTANT", "Sector Accountant"), ("SECTOR_REVIEWER", "Sector Reviewer"), ("SECTOR_CHIEF_ACCOUNTANT", "Sector Chief Accountant"), ("FINANCE_DIRECTOR", "Sector Finance Director"), ("SECTOR_DIRECTOR", "Sector Director")], default="MANAGER", max_length=30),
        ),
    ]
