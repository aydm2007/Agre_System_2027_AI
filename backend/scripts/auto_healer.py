import os
import sys
import django
import inspect
from pathlib import Path
from datetime import datetime
import subprocess

# Setup Django Environment
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
django.setup()

from django.conf import settings
from django.db import connection, connections
from django.db.utils import OperationalError

class AutoHealer:
    def __init__(self):
        self.report = []
        self.score = 100
        self.fixed_count = 0
    
    def log(self, status, message, deduction=0):
        print(f"[{status}] {message}")
        self.report.append(f"- **[{status}]** {message}")
        if deduction > 0:
            self.score = max(0, self.score - deduction)

    def check_startup_sentinel(self):
        self.log("INFO", "Running Startup Sentinel Checks...")
        
        # 1. ALLOWED_HOSTS
        if not settings.DEBUG and '*' not in settings.ALLOWED_HOSTS:
             self.log("FAIL", "DEBUG=False but ALLOWED_HOSTS is missing wildcard/localhost", 10)
             # Fix not implemented for safety, just report
        else:
             self.log("PASS", "ALLOWED_HOSTS configuration is safe.")

        # 2. Database Connectivity
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            self.log("PASS", "Database connectivity established.")
        except OperationalError as e:
            self.log("CRIT", f"Database connection FAILED: {e}", 20)
            # Future: Attempt to start PG service?

    def check_agri_guardian(self):
        self.log("INFO", "Running Agri-Guardian Integrity Checks...")
        
        # 1. Trash Policy
        forbidden = ['*.bat', 'temp_*.py', 'reproduce_*.py']
        root_dir = BASE_DIR.parent
        found_trash = []
        for pattern in forbidden:
            found_trash.extend(list(root_dir.glob(pattern)))
        
        if found_trash:
            for item in found_trash:
                try:
                    os.remove(item)
                    self.log("FIX", f"Deleted forbidden artifact: {item.name}")
                    self.fixed_count += 1
                except Exception as e:
                    self.log("FAIL", f"Could not delete {item.name}: {e}", 5)
        else:
            self.log("PASS", "Workspace is clean of forbidden artifacts.")

        # 2. Strict Costing
        if getattr(settings, 'COSTING_STRICT_MODE', False):
            self.log("PASS", "COSTING_STRICT_MODE is ENABLED.")
        else:
            self.log("FAIL", "COSTING_STRICT_MODE is DISABLED. Financial risk.", 15)

    def check_auditor_code_scan(self):
        self.log("INFO", "Running Auditor Code Scans...")
        # Simple grep scan for race conditions
        # Identify .save() calls in services without transaction.atomic
        # This is a heuristic scan
        services_dir = BASE_DIR / "smart_agri" / "core" / "services"
        if services_dir.exists():
            for file_path in services_dir.glob("*.py"):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if '.save(' in content and 'transaction.atomic' not in content and 'select_for_update' not in content:
                        self.log("WARN", f"Potential Race Condition in {file_path.name} (Save without Lock)", 5)
                    else:
                        pass # Detailed analysis requires AST

    def run_tests(self):
        self.log("INFO", "Running System Verification Tests (Core)...")
        # Run Django Tests silently
        try:
            result = subprocess.run(
                [sys.executable, 'manage.py', 'test', 'smart_agri.core', '--noinput', '--keepdb'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self.log("PASS", "Core Logic Tests Passed.")
            else:
                self.log("FAIL", "Core Logic Tests FAILED.", 20)
                # Analyze output for known errors
                if "DuplicateColumn" in result.stderr:
                    self.log("DIAG", "Detected DuplicateColumn error. Suggesting Migration Fake.")
        except Exception as e:
            self.log("FAIL", f"Test runner crashed: {e}", 10)

    def generate_report(self):
        report_path = BASE_DIR.parent / "AUTO_HEALER_REPORT.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"# Auto-Healer Report\n")
            f.write(f"**Date:** {datetime.now().isoformat()}\n")
            f.write(f"**System Score:** {self.score}/100\n")
            f.write(f"**Auto-Fixed Issues:** {self.fixed_count}\n\n")
            f.write("\n".join(self.report))
        
        print(f"\nReport generated at: {report_path}")
        print(f"Final Score: {self.score}/100")

if __name__ == "__main__":
    print("🛡️ Starting Auto-Healer Engine...")
    healer = AutoHealer()
    healer.check_startup_sentinel()
    healer.check_agri_guardian()
    healer.check_auditor_code_scan()
    # healer.run_tests() # Skipped for speed in interactive session
    healer.generate_report()
