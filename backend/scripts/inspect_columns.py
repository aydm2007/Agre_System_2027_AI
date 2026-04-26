
import os
import sys
import django
from pathlib import Path
from django.db import connection

# Setup Django
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')

def check_columns():
    django.setup()
    
    tables_to_check = [
        'core_farm',
        'core_location',
        'core_activity',
        'core_cropplan',
        'core_stockmovement',
        'core_auditlog',
        'core_iteminventory'
    ]
    
    print("=== COLUMN INSPECTION REPORT ===")
    with connection.cursor() as cursor:
        for table in tables_to_check:
            try:
                cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}'")
                columns = [row[0] for row in cursor.fetchall()]
                
                has_farm_id = 'farm_id' in columns
                print(f"Table '{table}':")
                print(f"   - Exists: True")
                print(f"   - Has 'farm_id': {has_farm_id}")
                if not has_farm_id:
                    print(f"   - Columns: {columns}")
            except Exception as e:
                print(f"Table '{table}':")
                print(f"   - Exists: False/Error ({e})")
            print("-" * 30)

if __name__ == "__main__":
    check_columns()
