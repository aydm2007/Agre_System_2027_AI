import os
import sys

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'backend')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')

import django
django.setup()

from smart_agri.core.models.farm import Farm
from smart_agri.core.models.planning import CropPlan
from smart_agri.core.models.activity import Activity
from smart_agri.core.models.log import DailyLog

def run_cleanup():
    # Names or Slugs of farms to KEEP (Sovereign Protection)
    print("💎 Identifying Sovereign Farms (Sardood & Al-Jarouba)...")
    from django.db.models import Q
    
    # Keeping by substring to catch "مزرعة سردود" and "مزرعة الجروبة"
    farms_to_delete = Farm.objects.exclude(
        Q(name__icontains="سردود") | 
        Q(name__icontains="الجروبة") |
        Q(slug__icontains="saradud") |
        Q(slug__icontains="jarouba")
    )
    count = farms_to_delete.count()
    
    if count == 0:
        print("✅ No experimental farms found to delete.")
        return
        
    print(f"🗑️  Found {count} experimental farms to remove.")
    
    for farm in farms_to_delete:
        print(f"🧬 Final Titan Purge for Farm: {farm.name} (ID: {farm.id})")
        
        from django.db import connection
        with connection.cursor() as cursor:
            # 1. Disable ALL constraints for this session
            cursor.execute("SET session_replication_role = 'replica';")
            
            try:
                # 2. Targeted Destruction (Focusing on the main clusters)
                # Financials
                cursor.execute("DELETE FROM core_financialledger WHERE farm_id = %s;", [farm.id])
                cursor.execute("DELETE FROM finance_suppliersettlement WHERE farm_id = %s;", [farm.id])
                cursor.execute("DELETE FROM finance_suppliersettlementpayment WHERE settlement_id IN (SELECT id FROM finance_suppliersettlement WHERE farm_id = %s);", [farm.id])
                
                # Inventory & Purchases 
                cursor.execute("DELETE FROM inventory_purchaseorder WHERE farm_id = %s;", [farm.id])
                cursor.execute("DELETE FROM core_stockmovement WHERE farm_id = %s;", [farm.id])
                cursor.execute("DELETE FROM core_item_inventory WHERE farm_id = %s;", [farm.id])
                cursor.execute("DELETE FROM inventory_tankcalibration WHERE asset_id IN (SELECT id FROM core_asset WHERE farm_id = %s);", [farm.id])
                
                # Activities & Logs
                cursor.execute("DELETE FROM core_fuelconsumptionalert WHERE log_id IN (SELECT id FROM core_dailylog WHERE farm_id = %s);", [farm.id])
                cursor.execute("DELETE FROM core_activity_cost_snapshot WHERE crop_plan_id IN (SELECT id FROM core_cropplan WHERE farm_id = %s);", [farm.id])
                cursor.execute("DELETE FROM core_activity WHERE log_id IN (SELECT id FROM core_dailylog WHERE farm_id = %s);", [farm.id])
                cursor.execute("DELETE FROM core_dailylog WHERE farm_id = %s;", [farm.id])
                
                # Human Resources
                cursor.execute("DELETE FROM core_timesheet WHERE farm_id = %s;", [farm.id])
                cursor.execute("DELETE FROM core_employee WHERE farm_id = %s;", [farm.id])
                
                # Structure
                cursor.execute("DELETE FROM core_cropplan WHERE farm_id = %s;", [farm.id])
                cursor.execute("DELETE FROM core_location WHERE farm_id = %s;", [farm.id])
                cursor.execute("DELETE FROM core_asset WHERE farm_id = %s;", [farm.id])
                cursor.execute("DELETE FROM accounts_farmmembership WHERE farm_id = %s;", [farm.id])
                
                # 3. Final Strike
                cursor.execute("DELETE FROM core_farm WHERE id = %s;", [farm.id])
                
            finally:
                # 4. Re-enable constraints
                cursor.execute("SET session_replication_role = 'origin';")

        print(f"   -> Sovereign Titan Purge Complete for ID: {farm.id}")
        
    print("🎉 Cleanup completed successfully! Only 'الجروبة' and 'سردود' remain.")

if __name__ == "__main__":
    run_cleanup()
