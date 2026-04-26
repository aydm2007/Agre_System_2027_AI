"""
Runner that writes output to a file so agent can read results.
"""
import subprocess
import sys
import os

os.chdir(r"c:\tools\workspace\Agre_ERP_2027-main\backend")
output_file = r"c:\tools\workspace\Agre_ERP_2027-main\backend\test_results.txt"

with open(output_file, "w", encoding="utf-8") as f:
    f.write("=" * 60 + "\n")
    f.write("  SEED DEMO DATA\n")
    f.write("=" * 60 + "\n")
    
    result = subprocess.run(
        [sys.executable, "manage.py", "seed_surdud_demo_data"],
        capture_output=True, text=True, timeout=60
    )
    f.write(result.stdout + "\n")
    if result.stderr:
        f.write("STDERR:\n" + result.stderr + "\n")
    f.write(f"Exit code: {result.returncode}\n\n")

    f.write("=" * 60 + "\n")
    f.write("  BACKEND TESTS\n")
    f.write("=" * 60 + "\n")
    
    result2 = subprocess.run(
        [sys.executable, "-m", "pytest",
         "smart_agri/inventory/tests/test_inventory_service.py",
         "smart_agri/sales/tests/test_sale_service.py",
         "smart_agri/accounts/tests/test_role_delegation.py",
         "smart_agri/core/tests/test_diesel_monitoring.py",
         "-v", "--tb=short"],
        capture_output=True, text=True, timeout=120
    )
    f.write(result2.stdout + "\n")
    if result2.stderr:
        f.write("STDERR:\n" + result2.stderr + "\n")
    f.write(f"Exit code: {result2.returncode}\n\n")
    
    f.write("DONE\n")

print("Results written to:", output_file)
