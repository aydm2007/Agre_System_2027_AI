import os
import django
import sys
from django.db import connection

# Setup Django
sys.path.append('c:\\tools\\workspace\\saradud2027\\backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from django.apps import apps
from smart_agri.core.models import LocationTreeStock, CropVariety

def run_audit():
    print("🛡️ AGRI-GUARDIAN COMPREHENSIVE AUDIT REPORT")
    print("============================================")
    
    score = 100
    issues = []

    # ---------------------------------------------------------
    # 1. DATABASE HYGIENE (Schema Sentinel)
    # ---------------------------------------------------------
    print("\n[1] Checking Database Hygiene...")
    
    # Get all model tables
    model_tables = set()
    for model in apps.get_models():
        model_tables.add(model._meta.db_table)
    
    # Get all actual tables
    with connection.cursor() as cursor:
        actual_tables = set(connection.introspection.table_names(cursor))
    
    # Find Zombies (In DB but not in Models)
    zombies = actual_tables - model_tables
    # Ignore django/auth/system tables
    ignored_prefixes = ['django_', 'auth_', 'social_', 'spatial_ref_sys']
    real_zombies = [z for z in zombies if not any(z.startswith(p) for p in ignored_prefixes)]
    
    if real_zombies:
        print(f"❌ FAIL: Found {len(real_zombies)} Zombie Tables: {real_zombies}")
        score -= (len(real_zombies) * 5)
        issues.append(f"Database Hygiene: Found {len(real_zombies)} zombie tables (e.g. {real_zombies[0]}).")
    else:
        print("✅ PASS: No Zombie Tables detected.")

    # ---------------------------------------------------------
    # 2. FINANCIAL INTEGRITY
    # ---------------------------------------------------------
    print("\n[2] Checking Financial Integrity...")
    try:
        from smart_agri.finance.models import FinancialLedger
        ledger_count = FinancialLedger.objects.count()
        print(f"   -> Ledger Rows: {ledger_count}")
        
        # Check Immutability (no updated_at different from created_at, if updated_at exists)
        # Assuming strict ledger doesn't even have updated_at or if it does, it shouldn't change.
        if hasattr(FinancialLedger, 'updated_at'):
             mutated = FinancialLedger.objects.filter(updated_at__gt=F('created_at')).count()
             if mutated > 0:
                 print(f"❌ FAIL: {mutated} Ledger rows have been mutated!")
                 score -= 20
                 issues.append("Financial Integrity: Ledger rows have been mutated.")
             else:
                 print("✅ PASS: Ledger Immutability verified.")
        else:
             print("ℹ️ INFO: Ledger immutable by design (no updated_at).")

    except ImportError:
        print("⚠️ SKIP: finance app not found or model missing.")
    except Exception as e:
        print(f"⚠️ ERROR: {e}")

    # ---------------------------------------------------------
    # 3. PERENNIAL DATA INTEGRITY (Ghost References)
    # ---------------------------------------------------------
    print("\n[3] Checking Perennial Integrity...")
    
    # Check 1: Stocks with missing Variety
    stocks = LocationTreeStock.objects.all()
    broken_varieties = 0
    
    for s in stocks:
        vid = s.crop_variety_id
        if vid:
            if not CropVariety.objects.filter(id=vid).exists():
                broken_varieties += 1
                
    if broken_varieties > 0:
        print(f"❌ FAIL: Found {broken_varieties} LocationTreeStock records pointing to missing Varieties.")
        score -= (broken_varieties * 10)
        issues.append("Perennial Integrity: Ghost References found in Tree Stock.")
    else:
        print("✅ PASS: All Tree Stocks reference valid Varieties.")

    # ---------------------------------------------------------
    # 4. ARCHITECTURAL INTEGRITY (The Monolith Protection)
    # ---------------------------------------------------------
    print("\n[4] Checking Service Layer Integrity...")
    # Grep for .objects.create in viewsets
    import glob
    view_files = glob.glob("smart_agri/core/api/viewsets/*.py")
    service_violations = 0
    
    for vf in view_files:
        with open(vf, 'r', encoding='utf-8') as f:
            content = f.read()
            if "LocationTreeStock.objects.create" in content:
                print(f"❌ FAIL: Service Layer Bypass in {vf} (LocationTreeStock)")
                service_violations += 1
            if "FinancialLedger.objects.create" in content:
                 print(f"❌ FAIL: Service Layer Bypass in {vf} (FinancialLedger)")
                 service_violations += 1
                 
    if service_violations > 0:
        score -= (service_violations * 15)
        issues.append(f"Architecture: {service_violations} Service Layer bypasses detected.")
    else:
        print("✅ PASS: No blatant Service Layer bypasses found in ViewSets.")

    # ---------------------------------------------------------
    # 5. FRONTEND CONTRACT (Basic Sanity)
    # ---------------------------------------------------------
    print("\n[5] Checking Frontend Contract...")
    # strict check: does DailyLog.jsx exist?
    # backend/ is CWD. ../frontend is sibling.
    frontend_path = "../frontend/src/pages/DailyLog.jsx"
    if os.path.exists(frontend_path):
        print("✅ PASS: DailyLog.jsx exists.")
    else:
        print(f"❌ FAIL: DailyLog.jsx missing at {os.path.abspath(frontend_path)}")
        score -= 50
        issues.append("Frontend: DailyLog.jsx is missing.")

    # ---------------------------------------------------------
    # SCORING
    # ---------------------------------------------------------
    final_score = max(0, score)
    print("\n============================================")
    print(f"FINAL AGRI-GUARDIAN SCORE: {final_score}/100")
    print("============================================")
    
    if issues:
        print("Issues Found:")
        for i in issues:
            print(f"- {i}")

if __name__ == '__main__':
    # Redirect stdout to file to capture full report
    import sys
    original_stdout = sys.stdout
    with open('agri_guardian_audit_result.txt', 'w', encoding='utf-8') as f:
        sys.stdout = f
        run_audit()
    sys.stdout = original_stdout
    # also print to console
    with open('agri_guardian_audit_result.txt', 'r', encoding='utf-8') as f:
        print(f.read())
