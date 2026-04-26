@echo off
setlocal EnableDelayedExpansion

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

echo [Bootstrap] Resolving backend database credentials...
for /f "usebackq tokens=*" %%i in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "& { . '%ROOT%\scripts\windows\Resolve-BackendDbEnv.ps1'; if ($env:DB_PASSWORD) { Write-Output ('DB_PASSWORD=' + $env:DB_PASSWORD) }; if ($env:DATABASE_URL) { Write-Output ('DATABASE_URL=' + $env:DATABASE_URL) } }"`) do (
    set "%%i"
)

if defined DB_PASSWORD (
    set "PGPASSWORD=%DB_PASSWORD%"
)

echo [Bootstrap] Running Pytest...
cd "%ROOT%\backend"
pytest %*
exit /b %ERRORLEVEL%
