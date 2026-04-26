from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_locationtreestock_deleted_at_and_more'),
        ('finance', '0013_actualexpense_deleted_at_actualexpense_deleted_by_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='BudgetClassification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=20, unique=True)),
                ('name_ar', models.CharField(max_length=200)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Budget Classification',
                'verbose_name_plural': 'Budget Classifications',
                'db_table': 'core_budgetclassification',
                'managed': True,
                'ordering': ['code'],
            },
        ),
        migrations.CreateModel(
            name='SectorRelationship',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('current_balance', models.DecimalField(decimal_places=4, default=0, help_text='الرصيد مع الإدارة العامة', max_digits=19)),
                ('allow_revenue_recycling', models.BooleanField(default=False, help_text='هل يسمح بتدوير الإيراد دون توريد؟')),
                ('farm', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, to='core.farm')),
            ],
            options={
                'verbose_name': 'Sector Relationship',
                'verbose_name_plural': 'Sector Relationships',
                'db_table': 'core_sectorrelationship',
                'managed': True,
            },
        ),
    ]
