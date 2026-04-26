import os
import django
import sys
from django.db import connection

# Setup Django
sys.path.append(r'C:\tools\workspace\AgriAsset_v44_test\backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

def definitive_check():
    print("💎 [SOVEREIGN AUDIT] Checking AuditLog and Approvals...")
    with connection.cursor() as cursor:
        tables = [
            'core_auditlog', 
            'finance_approvalrequest', 
            'core_biologicalassetcohort',
            'core_locationtreestock'
        ]
        for t in tables:
            cursor.execute(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{t}')")
            exists = cursor.fetchone()[0]
            print(f"📊 {t}: {'✅ OK' if exists else '❌ MISSING'}")

if __name__ == "__main__":
    definitive_check()
