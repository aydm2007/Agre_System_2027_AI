import os
import subprocess
import sys

TEST_DIR = r"c:\tools\workspace\saradud2027\testsprite_tests"
FILES = [
    "TC001_jwt_authentication_token_generation.py",
    "TC002_jwt_authentication_token_refresh.py",
    "TC003_core_api_access_core_resources.py",
    "TC004_advanced_reporting_get_advanced_report.py",
    "TC005_advanced_reporting_get_dashboard_stats.py"
]

print("🚀 Starting Manual Verification Run...")
passed = 0
failed = 0

for f in FILES:
    path = os.path.join(TEST_DIR, f)
    if not os.path.exists(path):
        print(f"❌ Missing: {f}")
        failed += 1
        continue
        
    print(f"👉 Running {f}...", end=" ", flush=True)
    try:
        result = subprocess.run([sys.executable, path], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ PASSED")
            passed += 1
        else:
            print("❌ FAILED")
            print(f"   Stderr: {result.stderr}")
            failed += 1
    except Exception as e:
        print(f"❌ ERROR: {e}")
        failed += 1

print("\n" + "="*30)
print(f"📊 SUMMARY: {passed} PASSED, {failed} FAILED")
if failed == 0:
    print("🎉 100% HEALTH CONFIRMED")
    sys.exit(0)
else:
    print("⚠️ ISSUES FOUND")
    sys.exit(1)
