from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0060_systemsettings_expense_auto_approve_limit'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cropvariety',
            name='crop',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='varieties_list', to='core.crop'),
        ),
    ]
