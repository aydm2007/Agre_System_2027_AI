import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from django.db import connection

try:
    with connection.cursor() as cursor:
        cursor.execute('ALTER TABLE core_farmsettings ADD COLUMN show_advanced_reports boolean DEFAULT false NOT NULL;')
        print('Column added successfully!')
except Exception as e:
    print('Error:', e)
