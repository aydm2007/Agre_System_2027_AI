from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0029_activity_idempotency_surrah_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="activity",
            name="cost_materials",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                help_text="تكلفة المواد (دقة 4 خانات)",
                max_digits=19,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="activity",
            name="cost_labor",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                help_text="تكلفة العمالة (دقة 4 خانات)",
                max_digits=19,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="activity",
            name="cost_machinery",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                help_text="تكلفة الآليات (دقة 4 خانات)",
                max_digits=19,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="activity",
            name="cost_overhead",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                help_text="التكاليف غير المباشرة (دقة 4 خانات)",
                max_digits=19,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="activity",
            name="cost_total",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                help_text="الإجمالي النهائي للنشاط (يجب أن يطابق مجموع البنود)",
                max_digits=19,
                null=True,
                verbose_name="إجمالي التكلفة",
            ),
        ),
    ]
