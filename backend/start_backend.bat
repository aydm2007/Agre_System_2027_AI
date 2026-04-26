@echo off
set "POSTGRES_HOST=127.0.0.1"
set "POSTGRES_PORT=5432"
set "POSTGRES_USER=postgres"
set "POSTGRES_DB=agriasset_db"
for /f "usebackq tokens=*" %%i in (`powershell -NoProfile -ExecutionPolicy Bypass -File "C:\tools\workspace\AgriAsset_v44\scripts\windows\Resolve-BackendDbEnv.ps1"`) do set PGPASSWORD=%%i
set "POSTGRES_PASSWORD=%PGPASSWORD%"
python manage.py runserver
