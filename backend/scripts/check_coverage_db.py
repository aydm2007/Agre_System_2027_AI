
import os
import sys
sys.path.append(os.path.join(os.getcwd(), 'backend'))
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

with connection.cursor() as cursor:
    cursor.execute("SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'core_treeservicecoverage';")
    columns = cursor.fetchall()
    print("Columns in core_treeservicecoverage:", columns)
