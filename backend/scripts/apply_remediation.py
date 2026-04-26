import os
import sys
import django
from django.db import connection

# Setup Django
sys.path.append(os.path.dirname(os.getcwd())) # Add backend root
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
django.setup()

def run_remediation():
    sql_path = os.path.join(os.path.dirname(__file__), 'remediation_v1.sql')
    print(f"Reading SQL from {sql_path}...")
    
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql = f.read()
        
    print("Executing SQL Remediation...")
    with connection.cursor() as cursor:
        cursor.execute(sql)
        
    print("✅ SQL Remediation Executed Successfully. Double-counting triggers are destroyed.")

if __name__ == "__main__":
    try:
        run_remediation()
    except Exception as e:
        print(f"❌ Error executing remediation: {e}")
        sys.exit(1)
