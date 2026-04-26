@echo off
cd /d "%~dp0"
set PGPASSWORD=Ibra3898@
if exist "..\.venv\Scripts\python.exe" set "PY_CMD=..\.venv\Scripts\python.exe"
if not defined PY_CMD if exist "..\venv\Scripts\python.exe" set "PY_CMD=..\venv\Scripts\python.exe"
if not defined PY_CMD (
  where py >nul 2>&1 && set "PY_CMD=py -3"
)
if not defined PY_CMD (
  where python >nul 2>&1 && set "PY_CMD=python"
)

echo ----------------------------------------
echo Using Python: %PY_CMD%
echo ----------------------------------------

echo Running Django Check...
%PY_CMD% manage.py check

echo Running Migration Check...
%PY_CMD% manage.py makemigrations --dry-run --check

echo Seeding Sardood Farm...
%PY_CMD% manage.py seed_sardood_farm --clean

echo Seeding Runtime Governance Evidence...
%PY_CMD% manage.py seed_runtime_governance_evidence

echo All Tasks Finished!
