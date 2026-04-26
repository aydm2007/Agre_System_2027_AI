from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0039_pettycashrequest_pettycashsettlement_pettycashline_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="financialledger",
            name="account_code",
            field=models.CharField(
                choices=[
                    ("1100-CASH", "Cash on Hand"),
                    ("1110-BANK", "Bank"),
                    ("2001-PAY-VENDOR", "Vendor Payable"),
                    ("4001-EXP-ADMIN", "Admin / Petty Cash Expense"),
                    ("EXP-ELEC", "Electricity Expense"),
                    ("1000-LABOR", "Labor Cost"),
                    ("2000-MATERIAL", "Material Cost"),
                    ("3000-MACHINERY", "Machinery Cost"),
                    ("4000-OVERHEAD", "Overhead Cost"),
                    ("5000-REVENUE", "Sales Revenue"),
                    ("1200-RECEIVABLE", "Accounts Receivable"),
                    ("1300-INV-ASSET", "Inventory Asset"),
                    ("6000-COGS", "Cost of Goods Sold"),
                    ("1400-WIP", "Work In Progress"),
                    ("7000-DEP-EXP", "Depreciation Expense"),
                    ("1500-ACC-DEP", "Accumulated Depreciation"),
                    ("2000-PAY-SAL", "Salaries Payable"),
                    ("2100-SECTOR-PAY", "حساب القطاع الإنتاجي"),
                    ("7100-ZAKAT-EXP", "Zakat Expense"),
                    ("2105-ZAKAT-PAY", "Zakat Payable"),
                    ("2110-VAT-PAY", "ضريبة القيمة المضافة (VAT)"),
                    ("9999-SUSPENSE", "Suspense - Requires Review"),
                ],
                db_index=True,
                max_length=50,
            ),
        ),
    ]
