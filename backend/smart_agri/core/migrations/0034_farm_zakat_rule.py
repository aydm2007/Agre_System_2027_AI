from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0033_employee_payment_mode_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='farm',
            name='zakat_rule',
            field=models.CharField(
                choices=[
                    ('5_PERCENT', 'نصف العشر (5%) - آبار/مضخات'),
                    ('10_PERCENT', 'العشر (10%) - مطر/سدود/غيل'),
                ],
                default='5_PERCENT',
                help_text='يحدد نسبة الزكاة الشرعية: 5% للكلفة، 10% للمطر.',
                max_length=20,
            ),
        ),
    ]
