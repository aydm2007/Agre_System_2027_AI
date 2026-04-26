import os

base_path = r"c:\tools\workspace\AgriAsset_v44"

# Scratch, dummy generators, and temporary build logs to clear
scratch_files = [
    "backend_check.log",
    "build_v40.txt",
    "buildout.txt",
    "lint_after_export.txt",
    "lintout.txt",
    "frontend_lint_after.txt",
    "setup_log.txt",
    "setup_out.txt",
    "probe_wells.py",
    "repro_500.py",
    "extract_safe.py",
    "fix_bom.py",
    "fix_throttle.py",
    "client_add_var.py",
    "client_planting_test.py",
    "debug_django.py",
    "dump_raw_db.py",
    "executor.py",
    "read_logs.py",
    "run_audit.py",
    "run_checks.py",
    "run_full_setup.py",
    "run_sardood_seed.py",
    "runner.py",
    "runner_variety.py",
    "script.py",
    "simulate_api_cycle.js",
    "simulate_api_cycle.py",
    "simulate_harvest.py",
    "time_repro.py",
    "remove_locks.py",
    "fetch_400.py",
    "test_db.py",
    "test_env.py",
    "test_e2e_cycle.py",
    "rebuild_node.py",
    "_fix_exceptions.py"
]

for f in scratch_files:
    target = os.path.join(base_path, f)
    if os.path.exists(target):
        try:
            os.remove(target)
            print(f"Removed transient file: {f}")
        except Exception as e:
            print(f"Failed to remove {f}: {e}")
