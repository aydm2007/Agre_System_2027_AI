from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0083_alter_employee_card_id_alter_employee_qr_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="farmsettings",
            name="approval_profile",
            field=models.CharField(
                choices=[
                    ("basic", "أساسي"),
                    ("tiered", "حسب شريحة المزرعة"),
                    ("strict_finance", "مالي صارم"),
                ],
                default="tiered",
                help_text="ملف الموافقات المعتمد لهذه المزرعة.",
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="farmsettings",
            name="contract_mode",
            field=models.CharField(
                choices=[
                    ("disabled", "معطل"),
                    ("operational_only", "تشغيلي فقط"),
                    ("full_erp", "ERP كامل"),
                ],
                default="operational_only",
                help_text="مستوى تفعيل العقود الزراعية والاستثمارية.",
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="farmsettings",
            name="cost_visibility",
            field=models.CharField(
                choices=[
                    ("ratios_only", "نسب فقط"),
                    ("summarized_amounts", "مبالغ ملخصة"),
                    ("full_amounts", "مبالغ كاملة"),
                ],
                default="summarized_amounts",
                help_text="درجة إظهار التكلفة للمستخدمين في الواجهات التشغيلية.",
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="farmsettings",
            name="fixed_asset_mode",
            field=models.CharField(
                choices=[
                    ("tracking_only", "تتبع فقط"),
                    ("full_capitalization", "رسملة كاملة"),
                ],
                default="tracking_only",
                help_text="مدى تفعيل دورة الأصل الثابت: تتبع فقط أو رسملة كاملة.",
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="farmsettings",
            name="treasury_visibility",
            field=models.CharField(
                choices=[
                    ("hidden", "مخفي"),
                    ("finance_only", "للفرق المالية فقط"),
                    ("visible", "ظاهر"),
                ],
                default="hidden",
                help_text="سياسة إظهار الخزينة والمقبوضات حسب المود والصلاحيات.",
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="farmsettings",
            name="variance_behavior",
            field=models.CharField(
                choices=[
                    ("warn", "تنبيه فقط"),
                    ("block", "منع التنفيذ"),
                    ("quarantine", "حجر ومراجعة"),
                ],
                default="warn",
                help_text="كيفية التعامل مع الانحرافات التشغيلية والمالية حسب سياسة المزرعة.",
                max_length=20,
            ),
        ),
    ]
