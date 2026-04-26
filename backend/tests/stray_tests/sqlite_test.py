import sqlite3
import datetime
import sys

db_path = r"c:\tools\workspace\Agre_ERP_2027-main\backend\db.sqlite3"

try:
    conn = sqlite3.connect(db_path, timeout=5)
    cursor = conn.cursor()

    # Get the default farm
    cursor.execute("SELECT id FROM core_farm ORDER BY id LIMIT 1;")
    farm_row = cursor.fetchone()
    if not farm_row:
        # Create a farm if it doesn't exist
        cursor.execute("INSERT INTO core_farm (name, code, area, is_active, is_deleted, created_at, updated_at) VALUES ('Default Farm', 'DF01', 100, 1, 0, datetime('now'), datetime('now'))")
        farm_id = cursor.lastrowid
    else:
        farm_id = farm_row[0]
    
    # 1. Add Mango
    cursor.execute("SELECT id FROM core_crop WHERE name='مانجو' AND is_deleted=0")
    mango_row = cursor.fetchone()
    if not mango_row:
        cursor.execute("INSERT INTO core_crop (name, mode, is_perennial, is_active, is_deleted, created_at, updated_at, farm_id) VALUES ('مانجو', 'Open', 1, 1, 0, datetime('now'), datetime('now'), ?)", (farm_id,))
        mango_id = cursor.lastrowid
    else:
        mango_id = mango_row[0]

    cursor.execute("SELECT id FROM core_cropvariety WHERE crop_id=? AND name='عويس'", (mango_id,))
    awees_row = cursor.fetchone()
    if not awees_row:
        cursor.execute("INSERT INTO core_cropvariety (crop_id, name, is_active, is_deleted, created_at, updated_at) VALUES (?, 'عويس', 1, 0, datetime('now'), datetime('now'))", (mango_id,))
        awees_id = cursor.lastrowid
        print("Inserted Awees", awees_id)
    else:
        awees_id = awees_row[0]

    # 2. Add Banana
    cursor.execute("SELECT id FROM core_crop WHERE name='موز' AND is_deleted=0")
    banana_row = cursor.fetchone()
    if not banana_row:
        cursor.execute("INSERT INTO core_crop (name, mode, is_perennial, is_active, is_deleted, created_at, updated_at, farm_id) VALUES ('موز', 'Open', 1, 1, 0, datetime('now'), datetime('now'), ?)", (farm_id,))
        banana_id = cursor.lastrowid
    else:
        banana_id = banana_row[0]

    cursor.execute("SELECT id FROM core_cropvariety WHERE crop_id=? AND name='كافنديش'", (banana_id,))
    cav_row = cursor.fetchone()
    if not cav_row:
        cursor.execute("INSERT INTO core_cropvariety (crop_id, name, is_active, is_deleted, created_at, updated_at) VALUES (?, 'كافنديش', 1, 0, datetime('now'), datetime('now'))", (banana_id,))
        cav_id = cursor.lastrowid
        print("Inserted Cavendish", cav_id)
    else:
        cav_id = cav_row[0]

    # 3. Add Daily Log
    today_str = datetime.date.today().isoformat()
    cursor.execute("INSERT INTO core_dailylog (farm_id, crop_id, log_date, notes, is_active, is_deleted, created_at, updated_at) VALUES (?, ?, ?, 'Added via Python sqlite3 script', 1, 0, datetime('now'), datetime('now'))", (farm_id, mango_id, today_str))
    log_id = cursor.lastrowid

    cursor.execute("INSERT INTO core_activity (log_id, activity_type, variety_id, trees_count, activity_name, is_active, is_deleted, created_at, updated_at, status) VALUES (?, 'Service', ?, 50, 'Perennial Inspection', 1, 0, datetime('now'), datetime('now'), 'PLANNED')", (log_id, awees_id))
    print("SUCCESS: Perennial crops and daily log inserted via direct sqlite3.")

    conn.commit()
    conn.close()
    sys.exit(0)

except Exception as e:
    print(f"Error accessing database: {e}")
    sys.exit(1)
