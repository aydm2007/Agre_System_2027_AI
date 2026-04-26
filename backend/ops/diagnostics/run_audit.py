import subprocess
import os

commands = [
    ["python", "manage.py", "showmigrations"],
    ["python", "manage.py", "check"],
    ["python", "scripts/check_no_float_mutations.py"],
    ["python", "scripts/check_idempotency_actions.py"],
    ["python", "scripts/detect_zombies.py"],
    ["python", "scripts/check_zakat_harvest_triggers.py"],
    ["python", "scripts/check_solar_depreciation_logic.py"]
]

print("Starting pre-implementation audit...")

all_passed = True
for cmd in commands:
    print(f"\nRunning: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FAILED (Exit {result.returncode})")
        print(result.stdout)
        print(result.stderr)
        all_passed = False
    else:
        print("SUCCESS")
        print(result.stdout[:500] + ("..." if len(result.stdout) > 500 else ""))

print(f"\nAudit Passed? {all_passed}")
