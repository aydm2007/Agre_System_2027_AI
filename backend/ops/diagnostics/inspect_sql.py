
import os
import sys

# Setup Django standalone
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
import django
django.setup()

SQL_PATH = r"C:\AgriAsset2025RLSFIX\workspace_v3.1.1.8.8.9.sql"
LOG_PATH = r"C:\AgriAsset2025RLSFIX\sql_inspection.log"

def inspect():
    with open(LOG_PATH, "w", encoding="utf-8") as log:
        def write_log(msg):
            log.write(msg)
            log.flush()
            os.fsync(log.fileno())

        write_log(f"Checking: {SQL_PATH}\n")
        if not os.path.exists(SQL_PATH):
            write_log("FILE NOT FOUND\n")
            return

        try:
            with open(SQL_PATH, "r", encoding="utf-8", errors="ignore") as f:
                write_log("--- HEADER (First 20 lines) ---\n")
                for i in range(20):
                    line = f.readline()
                    if not line: break
                    write_log(f"{i+1}: {line.strip()}\n")
                write_log("-----------------------------\n")
                
                # Scan for COPY statements
                f.seek(0)
                copy_found = False
                insert_found = False
                for i, line in enumerate(f):
                    if i > 5000: break # Scan first 5000 lines only
                    if "COPY " in line and " FROM stdin" in line:
                        write_log(f"FOUND COPY: {line.strip()}\n")
                        copy_found = True
                    if "INSERT INTO" in line:
                        write_log(f"FOUND INSERT: {line.strip()[:100]}\n")
                        insert_found = True
                    
                    if copy_found and insert_found: break
                    
        except Exception as e:
            log.write(f"ERROR READING FILE: {e}\n")

if __name__ == "__main__":
    inspect()
