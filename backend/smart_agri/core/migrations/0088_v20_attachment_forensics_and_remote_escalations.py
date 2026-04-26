from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0087_v14_attachment_archive_fields"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.AddField(
            model_name="farmsettings",
            name="attachment_scan_mode",
            field=models.CharField(choices=[("heuristic", "فحص هيوريستي"), ("clamav", "ClamAV / خارجي")], default="heuristic", help_text="محرك فحص المرفقات المطلوب لهذه المزرعة.", max_length=24),
        ),
        migrations.AddField(
            model_name="farmsettings",
            name="attachment_require_clean_scan_for_strict",
            field=models.BooleanField(default=True, help_text="منع مرور مرفق STRICT إذا لم يحصل على نتيجة فحص نظيفة."),
        ),
        migrations.AddField(
            model_name="farmsettings",
            name="attachment_enable_cdr",
            field=models.BooleanField(default=False, help_text="تشغيل مسار إعادة بناء المحتوى CDR للمرفقات الحساسة عند توفره تشغيلياً."),
        ),
        migrations.CreateModel(
            name="RemoteReviewEscalation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("level", models.CharField(choices=[("due", "مستحق"), ("overdue", "متأخر"), ("blocked", "محجوب")], default="due", max_length=20)),
                ("reason", models.CharField(blank=True, default="", max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("resolution_note", models.CharField(blank=True, default="", max_length=255)),
                ("farm", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="remote_review_escalations", to="core.farm")),
            ],
            options={
                "db_table": "core_remotereviewescalation",
                "ordering": ["-created_at"],
                "verbose_name": "تصعيد مراجعة قطاعية عن بعد",
                "verbose_name_plural": "تصعيدات المراجعة القطاعية عن بعد",
            },
        ),
        migrations.CreateModel(
            name="AttachmentLifecycleEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(choices=[("received", "Received"), ("scan_passed", "Scan Passed"), ("scan_quarantined", "Scan Quarantined"), ("authoritative_marked", "Authoritative Marked"), ("legal_hold_applied", "Legal Hold Applied"), ("legal_hold_released", "Legal Hold Released"), ("archived", "Archived"), ("restored", "Restored"), ("purged", "Purged")], max_length=40)),
                ("note", models.CharField(blank=True, default="", max_length=255)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="attachment_lifecycle_events", to="auth.user")),
                ("attachment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lifecycle_events", to="core.attachment")),
            ],
            options={
                "db_table": "core_attachmentlifecycleevent",
                "ordering": ["created_at"],
                "verbose_name": "حدث دورة حياة مرفق",
                "verbose_name_plural": "أحداث دورة حياة المرفقات",
            },
        ),
    ]
