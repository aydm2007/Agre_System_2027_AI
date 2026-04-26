
import os
import sys
import django
from django.db import connection

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

def fix_schema():
    with connection.cursor() as cursor:
        print("Dropping duplicate sequence core_laborrate_id_seq1...")
        try:
            cursor.execute("DROP SEQUENCE IF EXISTS core_laborrate_id_seq1;")
            print("Dropped successfully.")
        except Exception as e:
            print(f"Error dropping sequence: {e}")

if __name__ == '__main__':
    fix_schema()
