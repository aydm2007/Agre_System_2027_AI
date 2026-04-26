import re
import os

SQL_FILE_PATH = r"C:\AgriAsset2025RLSFIX\workspace_v3.1.1.8.8.9.sql"
OUTPUT_FILE = "sql_analysis.txt"

def analyze_sql():
    tables = set()
    
    if not os.path.exists(SQL_FILE_PATH):
        with open(OUTPUT_FILE, "w") as f:
            f.write(f"Error: File not found: {SQL_FILE_PATH}")
        return

    print(f"Analyzing {SQL_FILE_PATH}...")
    
    with open(SQL_FILE_PATH, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("--"):
                continue
            
            # Regex to capture table name from INSERT INTO statement
            match = re.search(r"INSERT INTO (public\.)?(\w+)", line, re.IGNORECASE)
            if match:
                table_name = match.group(2)
                tables.add(table_name)
    
    with open(OUTPUT_FILE, "w") as f:
        f.write("Tables found in SQL dump with INSERT statements:\n")
        for table in sorted(tables):
            f.write(f"- {table}\n")
    
    print(f"Analysis complete. Found {len(tables)} tables.")

if __name__ == "__main__":
    analyze_sql()
