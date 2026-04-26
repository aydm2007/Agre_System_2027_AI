from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0093_drop_legacy_official_labor_policy"),
    ]

    operations = [
        migrations.AddField(
            model_name="farmsettings",
            name="allow_creator_self_variance_approval",
            field=models.BooleanField(
                default=False,
                help_text="السماح استثنائيًا لمنشئ اليومية باعتماد الانحراف الحرج لنفسه فقط وفق سياسة المزرعة، دون السماح باعتماد السجل النهائي.",
            ),
        ),
        migrations.AddField(
            model_name="farmsettings",
            name="show_daily_log_smart_card",
            field=models.BooleanField(
                default=True,
                help_text="إظهار طبقة الكرت الذكي/السياق الذكي في اليومية عندما تفرضها المهمة والسياسة.",
            ),
        ),
    ]
