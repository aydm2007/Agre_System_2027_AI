
import os
import sys
import django
from pathlib import Path
from django.conf import settings

# Setup Django
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')

REPORT_FILE = BASE_DIR.parent / "doctor_report.txt"

def log(msg):
    with open(REPORT_FILE, "a") as f:
        f.write(msg + "\n")
    print(msg)

def diagnose():
    try:
        # Clear report
        with open(REPORT_FILE, "w") as f:
            f.write("=== AGRI-GUARDIAN DIAGNOSTIC REPORT ===\n")
            
        log("[1] Checking Django Setup...")
        django.setup()
        log("✅ Django Setup Complete.")
        
        log(f"[2] Checking Configuration...")
        log(f"   DEBUG: {settings.DEBUG}")
        log(f"   ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
        log(f"   DATABASES: {settings.DATABASES['default']['ENGINE']} @ {settings.DATABASES['default']['HOST']}")
        
        log("[3] Checking Database Connection...")
        from django.db import connections
        conn = connections['default']
        conn.cursor()
        log("✅ Database Connection Successful.")
        
        log("[4] Checking Migrations...")
        from django.db.migrations.executor import MigrationExecutor
        from django.db import connections, DEFAULT_DB_ALIAS
        
        connection = connections[DEFAULT_DB_ALIAS]
        connection.prepare_database()
        executor = MigrationExecutor(connection)
        targets = executor.loader.graph.leaf_nodes()
        
        log(f"   Target Migrations: {len(targets)}")
        
        unapplied = executor.migration_plan(targets)
        if unapplied:
            log(f"❌ Unapplied Migrations Found: {len(unapplied)}")
            for plan in unapplied:
                log(f"   - {plan[0]}")
        else:
            log("✅ All Migrations Applied.")
            
        log("[5] Checking Ports...")
        # Check if port 8000 is taken?
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 8000))
        if result == 0:
             log("⚠️ Port 8000 is OPEN (Something is running).")
        else:
             log("ℹ️ Port 8000 is CLOSED (Free to bind).")
        sock.close()
        
    except Exception as e:
        log(f"❌ CRITICAL FAILURE: {str(e)}")
        import traceback
        log(traceback.format_exc())

if __name__ == "__main__":
    diagnose()
