
import os
import sys
import django
from django.db import connection, transaction

# Setup Django standalone
sys.path.append(os.path.join(os.getcwd(), 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

def deep_clean_transactions():
    """
    Purges all 'Daily' and 'Transactional' data.
    Preserves 'Master' data (Farms, Users, Items, Crops).
    """
    print("🧹 Starting Deep Clean of Experimental Data...")
    
    # List of tables to TRUNCATE (Cascade will handle FKs usually, but let's be explicit)
    # Order matters for constraints if not using cascade
    
    # Subclasses of Activity first (Extensions)
    activity_extensions = [
        'core_activity_harvest',
        'core_activity_irrigation',
        'core_activity_planting',
        'core_activity_material',
        'core_activity_machine',
        'core_activity_item',
        'core_activitycostsnapshot',
    ]

    # Core Transaction Tables
    transactions = [
        'core_financialledger',
        'core_stockmovement',
        'core_iteminventorybatch', # Inventory Batches derived from movements
        'core_activity',           # The heart of operations
        'core_dailylog',           # The root of operations
        'core_harvestlot',         # Derived from Harvest Activities usually
    ]
    
    # Tables to RESET (Not Drop/Truncate, but Update)
    # core_item_inventory: We should probably truncate it if we assume all stock came from movements.
    # If initial stock was loaded manually via movements, then truncating movements means inventory is 0.
    # Safe bet: Truncate inventory too, let them re-initialize opening stock properly.
    inventory_tables = [
        'core_item_inventory',
    ]
    
    with connection.cursor() as cursor:
        cursor.execute("BEGIN;")
        
        try:
            # 1. Extensions
            for table in activity_extensions:
                print(f"   - Truncating {table}...")
                cursor.execute(f"TRUNCATE TABLE {table} CASCADE;")
                
            # 2. Transactions
            for table in transactions:
                print(f"   - Truncating {table}...")
                cursor.execute(f"TRUNCATE TABLE {table} CASCADE;")
            
            # 3. Inventory Reset
            for table in inventory_tables:
                 print(f"   - Truncating {table}...")
                 cursor.execute(f"TRUNCATE TABLE {table} CASCADE;")
            
            print("   ✅ All transactional tables truncated.")
            
            # 4. Optional: Reset Auto-Increment Sequences (for aesthetics)
            # PostgreSQL specific
            print("   - Resetting sequences...")
            tables_to_reset = transactions + activity_extensions + inventory_tables
            for table in tables_to_reset:
                 # Check if sequence exists standard django naming
                 seq_name = f"{table}_id_seq"
                 # Verify existence
                 cursor.execute("SELECT to_regclass(%s)", [seq_name])
                 if cursor.fetchone()[0]:
                     cursor.execute(f"ALTER SEQUENCE {seq_name} RESTART WITH 1;")
            
            # Commit
            cursor.execute("COMMIT;")
            print("\n✨ Deep Clean Complete. System returned to 'Factory Settings' (Master Data Only).")
            
        except Exception as e:
            cursor.execute("ROLLBACK;")
            print(f"\n❌ ERROR: Compliance check failed. Rollback executed.")
            print(f"Details: {e}")

if __name__ == "__main__":
    deep_clean_transactions()
