
import os
import django
from django.db import connection

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

def apply_patch():
    patch_path = r'c:\tools\workspace\saradud2025\db_patches\0010_create_season_table.sql'
    print(f"Applying patch: {patch_path}")
    
    with open(patch_path, 'r', encoding='utf-8') as f:
        sql = f.read()
        
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql)
        print("Successfully applied SQL patch.")
    except Exception as e:
        print(f"Error applying patch: {e}")

if __name__ == '__main__':
    apply_patch()
