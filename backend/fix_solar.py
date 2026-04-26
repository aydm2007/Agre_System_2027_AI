import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    # Check column status
    cursor.execute("""
        SELECT column_name, column_default, is_nullable, data_type
        FROM information_schema.columns 
        WHERE table_name='core_activity_irrigation' 
        AND column_name IN ('is_solar_powered','diesel_qty')
    """)
    rows = cursor.fetchall()
    print("Column status:")
    for row in rows:
        print(f"  {row}")

    if not any(r[0] == 'is_solar_powered' for r in rows):
        print("\nColumn 'is_solar_powered' MISSING — adding it...")
        cursor.execute("""
            ALTER TABLE core_activity_irrigation 
            ADD COLUMN is_solar_powered BOOLEAN NOT NULL DEFAULT FALSE
        """)
        print("  ✓ Added is_solar_powered column with DEFAULT FALSE")
    else:
        # Column exists but may have NULL values — fix them
        cursor.execute("""
            UPDATE core_activity_irrigation 
            SET is_solar_powered = FALSE 
            WHERE is_solar_powered IS NULL
        """)
        affected = cursor.rowcount
        print(f"\n  ✓ Fixed {affected} rows with NULL is_solar_powered → FALSE")

        # Also ensure the column has a proper NOT NULL default
        try:
            cursor.execute("""
                ALTER TABLE core_activity_irrigation 
                ALTER COLUMN is_solar_powered SET DEFAULT FALSE
            """)
            cursor.execute("""
                ALTER TABLE core_activity_irrigation 
                ALTER COLUMN is_solar_powered SET NOT NULL
            """)
            print("  ✓ Constraint set to NOT NULL DEFAULT FALSE")
        except Exception as e:
            print(f"  Note: {e}")

print("\nDone.")
