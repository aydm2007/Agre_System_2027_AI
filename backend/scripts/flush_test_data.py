import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from django.db import connection, transaction

def flush_transactional_data():
    """
    Cleans all transactional test tables (Logs, Ledgers, Invoices, Treasury) 
    using TRUNCATE CASCADE to ensure referential integrity is wiped cleanly, 
    but PRESERVES master data (Users, Groups, Farms, Accounts, Items).
    """
    print("\n⚠️  [WARNING] INITIATING DESTRUCTIVE DATA FLUSH ⚠️")
    print("This will erase ALL transactional records. Master data is preserved.\n")

    # The order doesn't strictly matter with CASCADE, but it's good practice
    tables_to_truncate = [
        "core_dailylog",
        "core_activity",
        "core_activityitem",
        "core_activityemployee",
        "core_idempotencyrecord",
        "finance_treasurytransaction",
        "finance_actualexpense",
        "finance_financialledger",
        "finance_financeauditlog", # Assuming audit log is here
        "sales_salesinvoice",
        "sales_salesinvoiceitem",
        "inventory_stockmovement",
        "inventory_iteminventorybatch",
        "inventory_fuellog",
    ]

    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                # We use PostgreSQL's TRUNCATE with CASCADE to wipe these tables 
                # and everything that relies on them, while also resetting the auto-increment sequences (RESTART IDENTITY).
                
                print(">> Preparing SQL Truncate Query...")
                # Filter out tables that might not exist just in case
                existing_tables = []
                for table in tables_to_truncate:
                    cursor.execute("SELECT to_regclass(%s);", [table])
                    if cursor.fetchone()[0] is not None:
                        existing_tables.append(table)
                    else:
                        print(f"   - Skipping {table} (not found in DB)")

                if not existing_tables:
                    print(">> No target tables found. Exiting.")
                    return

                truncate_sql = f"TRUNCATE TABLE {', '.join(existing_tables)} RESTART IDENTITY CASCADE;"
                
                print(f">> Executing: {truncate_sql[:50]}...")
                cursor.execute(truncate_sql)
                
                print("\n✅ SUCCESS: All transactional data has been successfully flushed.")
                print("Master data (Farms, Users, Roles, Chart of Accounts) remains intact.")
                print("System is now ready for Ultimate Edition Phase 2 (Analytical Dimensions).")

    except Exception as e:
        print(f"\n❌ ERROR: Data flush failed. Rolling back transaction.")
        print(f"Details: {e}")

if __name__ == '__main__':
    # A simple confirmation prompt to prevent accidental execution in production
    confirm = input("Are you absolutely sure you want to delete all transactional data? Type 'YES' to confirm: ")
    if confirm == "YES":
        flush_transactional_data()
    else:
        print("Flush cancelled.")
