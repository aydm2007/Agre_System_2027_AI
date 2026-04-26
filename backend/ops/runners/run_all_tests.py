"""Quick test runner for all new tests."""
import subprocess
import sys

test_files = [
    "smart_agri/inventory/tests/test_inventory_service.py",
    "smart_agri/sales/tests/test_sale_service.py",
    "smart_agri/accounts/tests/test_role_delegation.py",
    "smart_agri/core/tests/test_diesel_monitoring.py",
]

result = subprocess.run(
    [sys.executable, "-m", "pytest"] + test_files + ["-v", "--tb=short", "-q"],
    cwd=r"c:\tools\workspace\Agre_ERP_2027-main\backend",
)
sys.exit(result.returncode)
