@echo off
setlocal
cd /d "c:\tools\workspace\AgriAsset_v44\backend"

echo === STEP 1: Django Check ===
python manage.py check 2>&1
echo EXIT_CODE=%ERRORLEVEL%

echo === STEP 2: Runtime Probe V21 ===
python manage.py runtime_probe_v21 2>&1
echo EXIT_CODE=%ERRORLEVEL%

echo === STEP 3: ShowMigrations Plan ===
python manage.py showmigrations --plan 2>&1 | findstr /c:"[X]" /c:"[ ]" | find /c /v ""
echo EXIT_CODE=%ERRORLEVEL%

echo === STEP 4: Release Readiness Snapshot ===
python manage.py release_readiness_snapshot 2>&1
echo EXIT_CODE=%ERRORLEVEL%

echo === DONE ===
