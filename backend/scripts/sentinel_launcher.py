import os
import sys
import subprocess
import re
import time
import shutil
from pathlib import Path

# Sentinel Configuration
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANAGE_PY = PROJECT_ROOT / "manage.py"

def print_sentinel(msg):
    print(f"\n🛡️ [SENTINEL] {msg}")

def run_command(command, cwd=None):
    """Run command and return (exit_code, stdout, stderr)"""
    try:
        result = subprocess.run(
            command,
            cwd=cwd or PROJECT_ROOT,
            capture_output=True,
            text=True,
            shell=True,
            encoding='utf-8',
            errors='replace' # Handle encoding issues gracefully
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)

def parse_migration_error(stderr):
    """Parse stderr for known migration errors."""
    
    # CASE 1: DuplicateColumn
    # psycopg2.errors.DuplicateColumn: column "created_at" of relation "core_farm" already exists
    dup_col_match = re.search(r'psycopg2\.errors\.DuplicateColumn: column "(?P<col>\w+)" of relation "(?P<table>\w+)" already exists', stderr)
    if dup_col_match:
        return "DuplicateColumn", dup_col_match.group("col"), dup_col_match.group("table")

    # CASE 2: UndefinedTable
    # psycopg2.errors.UndefinedTable: relation "core_activitycostsnapshot" does not exist
    undef_table_match = re.search(r'psycopg2\.errors\.UndefinedTable: relation "(?P<table>\w+)" does not exist', stderr)
    if undef_table_match:
        return "UndefinedTable", None, undef_table_match.group("table")
        
    # CASE 3: UndefinedColumn
    # psycopg2.errors.UndefinedColumn: column "farm_id" does not exist
    undef_col_match = re.search(r'psycopg2\.errors\.UndefinedColumn: column "(?P<col>\w+)" does not exist', stderr)
    if undef_col_match:
        return "UndefinedColumn", undef_col_match.group("col"), None

    return None, None, None

def find_migration_file_in_traceback(stderr):
    """Find the specific migration file causing the crash from traceback."""
    # Applying core.0092_auto_20260128_0635...
    # OR explicit file paths in traceback if available (Django usually shows where it crashed in stack trace, but mainly we iterate migrations)
    # Better approach: Capture the last "Applying <app>.<migration>..." line from stdout/stderr.
    
    # Regex to find "Applying core.0092_auto..."
    matches = re.findall(r'Applying (?P<app>\w+)\.(?P<name>[\w_]+)\.\.\.', stderr + "\n" + stderr) # checking both? stderr usually has it? No, stdout has Applying. 
    # Actually, Django migrate output "Applying..." goes to stdout. The error goes to stderr.
    # We need to capture mixed output or look at stdout.
    
    return matches[-1] if matches else None

def fix_migration_file_duplicate_column(app, migration_name, column, table):
    """
    Locates the migration file and comments out AddField operations for the column.
    """
    print_sentinel(f"Fixing DuplicateColumn '{column}' in {app}.{migration_name}...")
    
    # Locate file
    # Assuming standard structure: backend/smart_agri/<app>/migrations/<name>.py
    # We might need to search for it if map isn't standard.
    # Let's search recursively in backend/smart_agri
    
    migration_filename = f"{migration_name}.py"
    found_path = None
    
    for path in PROJECT_ROOT.rglob(migration_filename):
        found_path = path
        break
        
    if not found_path:
        print_sentinel(f"Cannot find migration file: {migration_filename}")
        return False
        
    # Read file
    with open(found_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    # Heuristic fix: Locate "migrations.AddField" block that contains `model_name` (derived from table) and `name=column`.
    # Table "core_farm" -> model_name "farm"
    model_name = table.split('_', 1)[1] if '_' in table else table
    
    new_lines = []
    skip_mode = False
    modified = False
    
    # Very basic parser: if we see `migrations.AddField` and inside it we see correct model and name, we comment it out.
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Start of AddField
        if "migrations.AddField(" in line:
            # Check ahead for model_name and name
            chunk = ""
            j = i
            while j < len(lines):
                chunk += lines[j]
                if ")," in lines[j] or ")]" in lines[j]: # End of operation
                    break
                j += 1
            
            # Check if this chunk targets our culprit
            # Loose check for model_name and field name
            if f"model_name='{model_name}'" in chunk and f"name='{column}'" in chunk:
                # Comment out this block
                print_sentinel(f"  -> Disabling AddField for {model_name}.{column} at line {i+1}")
                new_lines.append(f"        # SENTINEL AUTO-FIX: DuplicateColumn {column} skipped\n")
                # Add commented out versions
                for k in range(i, j + 1):
                    new_lines.append("# " + lines[k])
                i = j + 1
                modified = True
                continue
                
        new_lines.append(line)
        i += 1
        
    if modified:
        with open(found_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        return True
    else:
        # Fallback: Validation might require a "Nuclear" empty list approach if parsing failed, 
        # but let's try the targeted approach first.
        print_sentinel("  -> Could not locate specific AddField block. Trying Regex Global Disable for this file?")
        return False

def fix_migration_file_undefined_table(app, migration_name, table):
    """
    Locates migration file and disable operations on missing table.
    """
    print_sentinel(f"Fixing UndefinedTable '{table}' in {app}.{migration_name}...")
    
    migration_filename = f"{migration_name}.py"
    found_path = None
    
    for path in PROJECT_ROOT.rglob(migration_filename):
        found_path = path
        break
        
    if not found_path:
        print_sentinel(f"Cannot find migration file: {migration_filename}")
        return False

    with open(found_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    modified = False
    
    i = 0
    while i < len(lines):
        line = lines[i]
        upper_line = line.upper()
        
        # Check if line targets the table and is a SQL command
        if table in line and ("ALTER TABLE" in upper_line or "DROP LINK" in upper_line or "DROP POLICY" in upper_line or "create policy" in line.lower()) and not line.strip().startswith("#") and not line.strip().startswith("--"):
             
             # Determine Comment Prefix
             if "migrations." in line:
                 prefix = "# "
                 is_sql_block = False
             else:
                 prefix = "-- "
                 is_sql_block = True

             # Special handling for multi-line CREATE POLICY
             if "create policy" in line.lower() and is_sql_block:
                 print_sentinel(f"  -> Commenting out multi-line CREATE POLICY for {table}")
                 new_lines.append(f"{prefix}SENTINEL AUTO-FIX: UndefinedTable {table} (Multi-line Policy)\n")
                 
                 # Loop until we find the semicolon or end of block
                 j = i
                 while j < len(lines):
                     sub_line = lines[j]
                     new_lines.append("-- " + sub_line)
                     if ";" in sub_line:
                         break
                     j += 1
                 i = j + 1
                 modified = True
                 continue

             # Standard Single Line Commenting
             print_sentinel(f"  -> Commenting out line referencing {table} (using '{prefix.strip()}')")
             new_lines.append(f"{prefix}SENTINEL AUTO-FIX: UndefinedTable {table}\n")
             new_lines.append(prefix + line)
             modified = True
             i += 1
        else:
            new_lines.append(line)
            i += 1
            
    if modified:
        with open(found_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        return True
    return False

def sentinel_loop():
    MAX_RETRIES = 5
    attempt = 1
    
    while attempt <= MAX_RETRIES:
        print_sentinel(f"Attempt {attempt}/{MAX_RETRIES}: Running Migrations...")
        
        # 1. Run Migrate
        # We must capture stdout too to find which migration is running
        code, stdout, stderr = run_command(f"{sys.executable} manage.py migrate")
        
        full_output = stdout + "\n" + stderr
        
        if code == 0:
            print_sentinel("✅ Migrations applied successfully.")
            break
        
        print_sentinel("❌ Migration Failed. Analyzing...")
        
        # 2. Analyze
        error_type, col, table = parse_migration_error(stderr)
        
        # Find which migration failed
        # We look at stdout for "Applying app.name..."
        # Reverse list to find the last "Applying"
        migration_match = None
        for line in reversed(stdout.split('\n')):
            m = re.search(r'Applying (?P<app>\w+)\.(?P<name>[\w_]+)\.\.\.', line)
            if m:
                migration_match = (m.group("app"), m.group("name"))
                break
        
        if not migration_match:
             print_sentinel("Could not identify which migration failed from stdout.")
             print("STDOUT LAST LINES:\n" + "\n".join(stdout.split('\n')[-5:]))
             print("STDERR:\n" + stderr)
             sys.exit(1)
             
        app, name = migration_match
        print_sentinel(f"Culprit Migration: {app}.{name}")
        
        # 3. Apply Fix
        fixed = False
        if error_type == "DuplicateColumn":
            fixed = fix_migration_file_duplicate_column(app, name, col, table)
        elif error_type == "UndefinedTable":
            fixed = fix_migration_file_undefined_table(app, name, table)
        elif error_type == "UndefinedColumn":
            print_sentinel(f"⚠️ UndefinedColumn '{col}' detected. This implies a schema mismatch.")
            print_sentinel("   Auto-Fix for columns is dangerous without knowing the table context.")
            print_sentinel("   Please inspect the migration manually or run 'scripts/inspect_columns.py'.")
            sys.exit(1)
        else:
            print_sentinel(f"Unknown error type or unhandled exception.\n{stderr}")
            sys.exit(1)
            
        if not fixed:
            print_sentinel("❌ Auto-Fix failed to modify the file. Exiting to avoid infinite loop.")
            sys.exit(1)
            
        print_sentinel("🩹 Fix applied. Retrying...")
        attempt += 1
        time.sleep(1)

    if attempt > MAX_RETRIES:
        print_sentinel("❌ Max retries reached. Driver failed.")
        sys.exit(1)
        
    # 4. Success -> Run Server
    print_sentinel("🚀 Starting Server (Loop Mode)...")
    # Using runserver 0.0.0.0:8000
    subprocess.run(f"{sys.executable} manage.py runserver 0.0.0.0:8000", shell=True, cwd=PROJECT_ROOT)

if __name__ == "__main__":
    sentinel_loop()
