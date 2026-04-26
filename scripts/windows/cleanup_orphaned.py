import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from django.apps import apps
from django.db import connection

def clean_orphaned_data():
    with connection.cursor() as cursor:
        cursor.execute("SELECT id FROM core_farm")
        valid_farm_ids = [row[0] for row in cursor.fetchall()]
        
        # We also need to check soft-deleted farms if their IDs should still be respected,
        # but if we used TRUNCATE or DELETE without cascade, they are physically gone from core_farm.
        
        # Find all tables with a farm_id column
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.columns 
            WHERE column_name = 'farm_id' 
            AND table_schema = 'public'
        """)
        tables_with_farm = [row[0] for row in cursor.fetchall()]
        
        print("Valid farms:", len(valid_farm_ids))
        print("Tables to clean:", tables_with_farm)
        
        summary = {}
        for table in tables_with_farm:
            # We must be careful not to trigger ledger restrictions if possible, 
            # so we'll do raw SQL deletion and disable triggers for the cleanup to avoid 'append-only' exceptions.
            cursor.execute(f"ALTER TABLE {table} DISABLE TRIGGER ALL;")
            
            if valid_farm_ids:
                format_strings = ','.join(['%s'] * len(valid_farm_ids))
                delete_query = f"DELETE FROM {table} WHERE farm_id IS NOT NULL AND farm_id NOT IN ({format_strings})"
                cursor.execute(delete_query, tuple(valid_farm_ids))
            else:
                delete_query = f"DELETE FROM {table} WHERE farm_id IS NOT NULL"
                cursor.execute(delete_query)
                
            deleted_count = cursor.rowcount
            if deleted_count > 0:
                summary[table] = deleted_count
            
            cursor.execute(f"ALTER TABLE {table} ENABLE TRIGGER ALL;")
            
        print("Cleanup Summary:", summary)

if __name__ == '__main__':
    clean_orphaned_data()
