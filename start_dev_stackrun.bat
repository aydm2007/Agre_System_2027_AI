@echo off
setlocal
set "ROOT=%~dp0"
cd /d "%ROOT%"
echo 🚀 Launching Agri-Guardian Sovereign Dev Stack (APP-ONLY + MIGRATE)...
echo.
echo [INFO] Running: Backend, Frontend, and Database Migrations.
echo [INFO] Celery/Redis bypassed for Windows compatibility. Database State is preserved.
echo.
call "%ROOT%start_dev_stack.bat" app-only migrate
pause
