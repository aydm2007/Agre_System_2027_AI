
import os
import sys
sys.path.append(os.path.join(os.getcwd(), 'backend'))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from smart_agri.core.models import Budget
print(f"Budget count: {Budget.objects.count()}")
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("SELECT column_name, is_nullable FROM information_schema.columns WHERE table_name = 'core_budget' AND column_name IN ('farm_id', 'season_id');")
    print(f"DB Nullability: {cursor.fetchall()}")
