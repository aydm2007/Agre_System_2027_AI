import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.config.settings')
django.setup()

from smart_agri.core.models.hr import Employee

emp_ids = [7, 12, 16, 13]
emps = Employee.objects.filter(id__in=emp_ids)

print("Check Employees:", emp_ids)
for e in emps:
    print(f"ID: {e.id}, Farm ID: {e.farm_id}, Active: {e.is_active}")
