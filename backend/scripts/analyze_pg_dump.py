import sys
import os

filename = r"c:\tools\workspace\saradud2027\dump_copy.main.sql"

print(f"Analyzing {filename}...")
if not os.path.exists(filename):
    print("File not found!")
    sys.exit(1)

file_size = os.path.getsize(filename)
print(f"File Size: {file_size / (1024*1024):.2f} MB")

tables = []
legacy_tables = []
indexes = 0
views = 0
data_rows = 0

try:
    with open(filename, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if line.startswith("CREATE TABLE"):
                parts = line.split()
                if len(parts) > 2:
                    table_name = parts[2].strip('";')
                    tables.append(table_name)
                    if "_old" in table_name or "legacy" in table_name or "_backup" in table_name or table_name.endswith("_bak"):
                        legacy_tables.append(table_name)
            elif line.startswith("CREATE INDEX"):
                indexes += 1
            elif line.startswith("CREATE VIEW"):
                views += 1
            elif line.startswith("COPY"):
                pass # Postgres data copy
            
            # Simple data volume heuristic
            if line[:1].isdigit() and "\t" in line:
               data_rows += 1

    print(f"\n--- Statistics ---")
    print(f"Total Tables: {len(tables)}")
    print(f"Legacy/Backup Tables: {len(legacy_tables)}")
    print(f"Indexes: {indexes}")
    print(f"Views: {views}")
    
    print("\n--- Legacy Tables Detected ---")
    for t in legacy_tables:
        print(f"- {t}")

    print("\n--- Core Tables (Sample) ---")
    core_tables = [t for t in tables if t.startswith("core")]
    for t in core_tables[:10]:
        print(f"- {t}")
        
    print("\nAnalysis Complete.")

except Exception as e:
    print(f"Error reading file: {e}")
