from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0043_alter_activity_options_alter_activityitem_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='asset',
            name='operational_cost_per_hour',
            field=models.DecimalField(decimal_places=2, default=0, help_text='تكلفة التشغيل التقديرية لكل ساعة (وقود + صيانة)', max_digits=10),
        ),
    ]
