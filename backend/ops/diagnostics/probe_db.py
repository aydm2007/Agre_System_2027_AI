import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

def probe():
    with connection.cursor() as cursor:
        try:
            # Check if core_farmsettings table exists and has sales_tax_percentage
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='core_farmsettings' AND column_name='sales_tax_percentage'")
            res = cursor.fetchone()
            if res:
                print("SUCCESS: sales_tax_percentage column found in core_farmsettings.")
            else:
                print("FAILURE: sales_tax_percentage column NOT found in core_farmsettings.")
        except Exception as e:
            print(f"ERROR probing database: {e}")

if __name__ == "__main__":
    probe()
