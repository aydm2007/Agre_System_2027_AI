from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0028_employmentcontract_overtime_shift_value_remove_activity_machine"),
    ]

    operations = [
        migrations.AddField(
            model_name="activity",
            name="idempotency_key",
            field=models.UUIDField(
                blank=True,
                help_text="Agri-Guardian: مفتاح منع التكرار لبيئة الشبكة الضعيفة",
                null=True,
            ),
        ),
        migrations.AddConstraint(
            model_name="activity",
            constraint=models.UniqueConstraint(
                fields=("idempotency_key",),
                condition=Q(idempotency_key__isnull=False),
                name="core_activity_idempotency_key_uniq",
            ),
        ),
        migrations.RemoveField(
            model_name="activityemployee",
            name="hours",
        ),
        migrations.RemoveField(
            model_name="activityemployee",
            name="surra_units",
        ),
        migrations.AddField(
            model_name="activityemployee",
            name="surrah_share",
            field=models.DecimalField(
                decimal_places=2,
                default=1,
                help_text="كم تعادل مشاركة العامل في هذا النشاط من إجمالي صرته اليومية",
                max_digits=4,
                verbose_name="حصة الصرة",
            ),
        ),
        migrations.RemoveField(
            model_name="timesheet",
            name="hours_overtime",
        ),
        migrations.RemoveField(
            model_name="timesheet",
            name="hours_regular",
        ),
        migrations.RemoveField(
            model_name="timesheet",
            name="surra_units",
        ),
        migrations.AddField(
            model_name="timesheet",
            name="surrah_count",
            field=models.DecimalField(
                decimal_places=2,
                default=1,
                help_text="عدد الصرات: 1.0 = يوم كامل، 0.5 = نصف يوم",
                max_digits=4,
            ),
        ),
        migrations.AddField(
            model_name="timesheet",
            name="surrah_overtime",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="إضافي بنظام الصرة (مثلاً 0.25 لربع يوم إضافي)",
                max_digits=4,
            ),
        ),
    ]
