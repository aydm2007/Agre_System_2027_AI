import os
import sys

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')

import django
try:
    django.setup()
except Exception as e:
    with open('audit_results.txt', 'w', encoding='utf-8') as f:
        f.write(f"Django setup failed: {e}")
    sys.exit(1)

from scripts.detect_zombies import run_audit as run_zombie_audit
from scripts.verification.detect_ghost_triggers import main as detect_ghost_triggers
from scripts.check_no_float_mutations import check_files as check_no_float
from scripts.check_idempotency_actions import check_idempotency
from scripts.check_audit_trail_coverage import main as check_audit_trail
from scripts.check_fund_accounting import main as check_fund_accounting

import contextlib
import io

def run_all_audits():
    with open('audit_results.txt', 'w', encoding='utf-8') as f:
        f.write("=== DEEP FORENSIC AUDIT RESULTS ===\n\n")

        f.write("--- 1. Zombie and Ghost Tables (Axis 1) ---\n")
        try:
            old_stdout = sys.stdout
            new_stdout = io.StringIO()
            sys.stdout = new_stdout
            run_zombie_audit()
            sys.stdout = old_stdout
            f.write(new_stdout.getvalue())
        except Exception as e:
            sys.stdout = old_stdout
            f.write(f"Error checking zombies: {e}\n")

        f.write("\n--- 2. Ghost Triggers (Axis 1) ---\n")
        try:
            old_stdout = sys.stdout
            new_stdout = io.StringIO()
            sys.stdout = new_stdout
            detect_ghost_triggers()
            sys.stdout = old_stdout
            f.write(new_stdout.getvalue())
        except Exception as e:
            sys.stdout = old_stdout
            f.write(f"Error checking triggers: {e}\n")

        f.write("\n--- 3. Decimal Integrity (Axis 5) ---\n")
        try:
            old_stdout = sys.stdout
            new_stdout = io.StringIO()
            sys.stdout = new_stdout
            check_no_float('.')
            sys.stdout = old_stdout
            f.write(new_stdout.getvalue())
        except Exception as e:
            sys.stdout = old_stdout
            f.write(f"Error checking floats: {e}\n")

        f.write("\n--- 4. Idempotency Actions (Axis 2) ---\n")
        try:
            old_stdout = sys.stdout
            new_stdout = io.StringIO()
            sys.stdout = new_stdout
            check_idempotency('.')
            sys.stdout = old_stdout
            f.write(new_stdout.getvalue())
        except Exception as e:
            sys.stdout = old_stdout
            f.write(f"Error checking idempotency: {e}\n")
            
        f.write("\n--- 5. Audit Trail Coverage (Axis 7) ---\n")
        try:
            old_stdout = sys.stdout
            new_stdout = io.StringIO()
            sys.stdout = new_stdout
            check_audit_trail()
            sys.stdout = old_stdout
            f.write(new_stdout.getvalue())
        except Exception as e:
            sys.stdout = old_stdout
            f.write(f"Error checking audit trails: {e}\n")
            
        f.write("\n--- 6. Fund Accounting Checks (Axis 4) ---\n")
        try:
            old_stdout = sys.stdout
            new_stdout = io.StringIO()
            sys.stdout = new_stdout
            check_fund_accounting()
            sys.stdout = old_stdout
            f.write(new_stdout.getvalue())
        except Exception as e:
            sys.stdout = old_stdout
            f.write(f"Error checking fund accounting: {e}\n")

if __name__ == '__main__':
    run_all_audits()
    print("Done")
