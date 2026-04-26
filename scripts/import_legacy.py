import sys
import os
import re

# Add backend to path so we can import smart_agri
sys.path.append(os.path.join(os.getcwd(), 'backend'))

import django
from django.db import connection, transaction

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
django.setup()

SQL_FILE_PATH = r"C:\AgriAsset2025RLSFIX\workspace_v3.1.1.8.8.9.sql"

# List of tables to import data for (order matters for FKs)
TARGET_TABLES = [
    "auth_user",
    "accounts_farm",
    "accounts_farmmembership",  # Critical for user access
    "core_unit",                # Reference data
    "inventory_store",          # Warehouses
    "core_location",
    "core_season",
    "core_machine",
    "core_crop",
    "core_activity",
    "core_activity_harvest", 
    "core_activity_planting",
    "core_activity_irrigation",
    "core_activity_fertilization",
    "core_activity_scouting"
]

def import_data():
    with open("import_debug.log", "w", encoding="utf-8") as log_file:
        def log(msg):
            print(msg)
            log_file.write(msg + "\n")
            log_file.flush()
            os.fsync(log_file.fileno())

        log(f"Starting import from {SQL_FILE_PATH}...")
        
        if not os.path.exists(SQL_FILE_PATH):
            log(f"Error: File not found: {SQL_FILE_PATH}")
            return

        with open(SQL_FILE_PATH, 'r', encoding='utf-8', errors='ignore') as f:
            cursor = connection.cursor()
            
            # Disable FK checks temporarily if possible
            try:
                cursor.execute("SET session_replication_role = 'replica';")
                log("FK checks disabled (replica role set).")
            except Exception as e:
                log(f"Warning: Could not set session_replication_role: {e}")

            inserts_found = 0
            copy_rows_found = 0
            
            in_copy_mode = False
            current_copy_table = None
            copy_buffer = []

            for line_num, line in enumerate(f):
                line = line.strip()
                if not line or line.startswith("--"):
                    continue
                
                # Check for COPY start
                if line.startswith("COPY ") and " FROM stdin;" in line:
                    match = re.search(r"COPY (public\.)?(\w+)", line, re.IGNORECASE)
                    if match:
                        table_name = match.group(2)
                        if table_name in TARGET_TABLES:
                            in_copy_mode = True
                            current_copy_table = table_name
                            log(f"--> Found COPY block for target table: {table_name}")
                        else:
                            log(f"Skipping COPY block for non-target table: {table_name}")
                    continue
                
                # Check for COPY end
                if in_copy_mode and line == "\.":
                    in_copy_mode = False
                    if copy_buffer:
                        try:
                            # Use copy_from for better performance? 
                            # But standard cursor copy_from expects a file-like object.
                            # We'll stick to parsing columns for now if possible, 
                            # or just skip COPY via python and rely on raw SQL execution if simple.
                            # Actually, executing raw Copy lines as INSERTs is hard.
                            # Better approach: Parse tab-separated values.
                            pass 
                        except Exception as e:
                            log(f"Error processing COPY block for {current_copy_table}: {e}")
                    copy_buffer = []
                    current_copy_table = None
                    continue

                if in_copy_mode:
                    # Parse COPY line (tab separated)
                    # This is complex because we need to know column names/types.
                    # Simpler fallback: If it is COPY, we might need 'psql' to restore it properly.
                    # BUT, we can try to guess columns? No.
                    # Plan B: Just log that we found it.
                    copy_rows_found += 1
                    if copy_rows_found % 100 == 0:
                        log(f"Processed {copy_rows_found} COPY rows (skipped actual insert for now as Python COPY parsing is risky)...")
                    continue

                # Check for INSERT
                is_target = False
                for table in TARGET_TABLES:
                    if re.search(f"INSERT INTO (public\.)?{table}", line, re.IGNORECASE):
                        is_target = True
                        break
                
                if is_target:
                    try:
                        cursor.execute(line)
                        inserts_found += 1
                        if inserts_found % 100 == 0:
                            log(f"Imported {inserts_found} INSERT rows...")
                    except Exception as e:
                        log(f"Error importing line {line_num}: {line[:50]}... Reason: {e}")

            # Re-enable FK checks
            try:
                cursor.execute("SET session_replication_role = 'origin';")
            except:
                pass
            cursor.close()
            
            log(f"Finished. Total INSERTs: {inserts_found}. Total COPY rows seen: {copy_rows_found}.")
            if copy_rows_found > 0:
                 log("WARNING: COPY statements were found but skipped by this Python script. Use 'psql' for full restore if possible.")

if __name__ == "__main__":
    try:
        import_data()
    except Exception as e:
        with open("debug_import_crash.log", "w") as f:
            f.write(f"CRASH: {e}")
