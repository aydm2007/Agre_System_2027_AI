from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0084_farmsettings_governance_policy_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="farmsettings",
            name="remote_site",
            field=models.BooleanField(default=False, help_text="هل المزرعة بعيدة/صعبة الوصول بحيث تحتاج ضوابط تعويضية عن الحضور الميداني؟"),
        ),
        migrations.AddField(
            model_name="farmsettings",
            name="single_finance_officer_allowed",
            field=models.BooleanField(default=False, help_text="للمزارع الصغرى فقط: السماح بأن يقوم شخص مالي واحد محلياً بدور محاسب/رئيس حسابات/قائم بأعمال المدير المالي."),
        ),
        migrations.AddField(
            model_name="farmsettings",
            name="local_finance_threshold",
            field=models.DecimalField(decimal_places=4, default=Decimal("100000.0000"), help_text="السقف المحلي الذي يمكن اعتماده داخل المزرعة قبل التصعيد إلى القطاع.", max_digits=19),
        ),
        migrations.AddField(
            model_name="farmsettings",
            name="sector_review_threshold",
            field=models.DecimalField(decimal_places=4, default=Decimal("250000.0000"), help_text="السقف الذي بعده تدخل مراجعة القطاع إلزامياً قبل الاعتماد النهائي.", max_digits=19),
        ),
        migrations.AddField(
            model_name="farmsettings",
            name="mandatory_attachment_for_cash",
            field=models.BooleanField(default=True, help_text="إلزام إرفاق مستندات للعمليات النقدية في المود الصارم."),
        ),
        migrations.AddField(
            model_name="farmsettings",
            name="weekly_remote_review_required",
            field=models.BooleanField(default=False, help_text="للمزارع البعيدة: إلزام مراجعة قطاعية أسبوعية عن بعد."),
        ),
        migrations.AddField(
            model_name="farmsettings",
            name="attachment_transient_ttl_days",
            field=models.PositiveIntegerField(default=30, help_text="عمر النسخ المؤقتة/المسودات من المرفقات قبل purge أو archival."),
        ),
        migrations.AddField(
            model_name="farmsettings",
            name="approved_attachment_archive_after_days",
            field=models.PositiveIntegerField(default=7, help_text="بعد كم يوم من الاعتماد النهائي تُنقل النسخة الحاكمة إلى طبقة أرشيفية منخفضة الكلفة."),
        ),
        migrations.AddField(
            model_name="farmsettings",
            name="attachment_max_upload_size_mb",
            field=models.PositiveIntegerField(default=10, help_text="أقصى حجم رفع للمرفقات بالميجابايت حسب سياسة المزرعة."),
        ),
        migrations.AddField(
            model_name="attachment",
            name="evidence_class",
            field=models.CharField(choices=[("transient", "مؤقت/مسودة"), ("operational", "تشغيلي"), ("financial_record", "سجل مالي حاكم"), ("legal_hold", "حجز قانوني/تدقيقي")], default="operational", max_length=24),
        ),
        migrations.AddField(
            model_name="attachment",
            name="is_authoritative_evidence",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="attachment",
            name="sha256_checksum",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="attachment",
            name="expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="attachment",
            name="archived_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
