import os
import re
import sys
import django
from datetime import date
from decimal import Decimal

# Setup Django Environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from django.conf import settings
from smart_agri.core.models import Activity, Crop
from smart_agri.finance.models import FinancialLedger

def audit_log(msg, status="INFO"):
    print(f"[{status}] {msg}")

def scan_file_for_pattern(filepath, pattern, description):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        if re.search(pattern, content):
            return True
    return False

def check_phi_blocking_logic():
    """
    Checks if Pre-Harvest Interval (PHI) logic is blocking (ValidationError) or Advisory (Warning).
    Yemen Context requires ADVISORY.
    """
    # Scanning Activity Model or Service for PHI logic
    # We look for 'ValidationError' combined with 'PHI' or 'تحريم'
    
    # Check activity.py
    activity_path = os.path.join(settings.BASE_DIR, 'smart_agri', 'core', 'models', 'activity.py')
    service_path = os.path.join(settings.BASE_DIR, 'smart_agri', 'core', 'services', 'harvest_service.py') # Hypothetical
    
    is_blocking = False
    
    if os.path.exists(activity_path):
        if scan_file_for_pattern(activity_path, r'ValidationError.*PHI', "PHI Blocking in Models"):
            audit_log("PHI Logic is BLOCKING in models.py (Violation of Yemen Context)", "FAIL")
            is_blocking = True
        elif scan_file_for_pattern(activity_path, r'ValidationError.*تحريم', "PHI Blocking in Models"):
            audit_log("PHI Logic is BLOCKING in models.py (Violation of Yemen Context)", "FAIL")
            is_blocking = True
        else:
            audit_log("PHI Logic appears non-blocking in models.py", "PASS")
            
    return is_blocking

def check_qc_mandatory_logic():
    """
    Checks if QC is mandatory.
    Yemen Context requires OPTIONAL.
    """
    # Scanning for 'qc_certificate' required=True or ValidationError if missing
    inventory_models_path = os.path.join(settings.BASE_DIR, 'smart_agri', 'inventory', 'models.py')
    
    if os.path.exists(inventory_models_path):
        if scan_file_for_pattern(inventory_models_path, r'qc_cert.*null=False', "Mandatory QC Field"):
            audit_log("QC Certificate is MANDATORY in DB Schema (Violation)", "FAIL")
        else:
            audit_log("QC Certificate is OPTIONAL (Correct for Context)", "PASS")

def check_financial_integrity():
    """
    Verifies Triple Match Capabilities (Ledger Existence)
    """
    # Check if Inventory Asset Account exists
    has_inv_account = False
    for choice in FinancialLedger.ACCOUNT_CHOICES:
        if choice[0] == '1300-INV-ASSET':
            has_inv_account = True
            break
    
    if has_inv_account:
        audit_log("Financial Ledger supports Inventory Asset Account (Triple Match Ready)", "PASS")
    else:
        audit_log("Financial Ledger missing Inventory Asset Account", "FAIL")

def check_frontend_isolation():
    """
    Scans Key Frontend Files for 'useFarmContext' usage.
    """
    frontend_dir = os.path.join(settings.BASE_DIR, '..', 'frontend', 'src', 'pages')
    
    files_to_check = [
        ('Finance/LedgerList.jsx', 'Ledger List'),
        ('Employees/EmployeeList.jsx', 'Employee List')
    ]
    
    for rel_path, name in files_to_check:
        full_path = os.path.join(frontend_dir, rel_path.replace('/', os.sep))
        if os.path.exists(full_path):
            has_context = scan_file_for_pattern(full_path, r'useFarmContext', "Farm Context Usage")
            has_alert = scan_file_for_pattern(full_path, r'!selectedFarmId', "No Farm Alert")
            
            if has_context and has_alert:
                audit_log(f"Frontend '{name}' implements Strict Isolation", "PASS")
            else:
                audit_log(f"Frontend '{name}' MISSING Isolation Checks", "FAIL")
        else:
            audit_log(f"File not found: {rel_path}", "WARN")

if __name__ == '__main__':
    print("=== AGRI-GUARDIAN DEEP SCAN (YEMEN CONTEXT) ===")
    check_phi_blocking_logic()
    check_qc_mandatory_logic()
    check_financial_integrity()
    check_frontend_isolation()
    print("=== SCAN COMPLETE ===")
