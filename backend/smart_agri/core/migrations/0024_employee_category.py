from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_locationtreestock_deleted_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='category',
            field=models.CharField(
                choices=[('OFFICIAL', 'موظف رسمي (راتب مركزي)'), ('CASUAL', 'أجر يومي (تمويل ذاتي)')],
                default='CASUAL',
                max_length=20,
            ),
        ),
    ]
