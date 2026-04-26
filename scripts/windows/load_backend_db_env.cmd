@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%\..\..") do set "ROOT=%%~fI"
set "BACKEND_ENV=%ROOT%\backend\.env"
set "QUIET=0"
if /i "%~1"=="--quiet" set "QUIET=1"

if exist "%BACKEND_ENV%" (
  for /f "usebackq tokens=1,* delims==" %%A in ("%BACKEND_ENV%") do (
    set "KEY=%%A"
    set "VALUE=%%B"
    if /i "!KEY!"=="DATABASE_URL" set "DATABASE_URL=!VALUE!"
    if /i "!KEY!"=="DB_HOST" set "DB_HOST=!VALUE!"
    if /i "!KEY!"=="DB_PORT" set "DB_PORT=!VALUE!"
    if /i "!KEY!"=="DB_NAME" set "DB_NAME=!VALUE!"
    if /i "!KEY!"=="DB_USER" set "DB_USER=!VALUE!"
    if /i "!KEY!"=="DB_PASSWORD" set "DB_PASSWORD=!VALUE!"
    if /i "!KEY!"=="PGPASSWORD" set "PGPASSWORD=!VALUE!"
  )
  if defined DATABASE_URL (
    if "%QUIET%"=="0" echo [OK] Backend DB environment loaded from backend\.env via DATABASE_URL
    endlocal & (
      set "DATABASE_URL=%DATABASE_URL%"
      exit /b 0
    )
  )
  if defined DB_PASSWORD (
    if not defined PGPASSWORD set "PGPASSWORD=%DB_PASSWORD%"
    if "%QUIET%"=="0" echo [OK] Backend DB password loaded from backend\.env
    endlocal & (
      if defined DB_HOST set "DB_HOST=%DB_HOST%"
      if defined DB_PORT set "DB_PORT=%DB_PORT%"
      if defined DB_NAME set "DB_NAME=%DB_NAME%"
      if defined DB_USER set "DB_USER=%DB_USER%"
      set "DB_PASSWORD=%DB_PASSWORD%"
      set "PGPASSWORD=%PGPASSWORD%"
      exit /b 0
    )
  )
  if "%QUIET%"=="0" echo [OK] Backend DB environment partially loaded from backend\.env
)

if defined DATABASE_URL (
  if "%QUIET%"=="0" echo [OK] Backend DB environment available via DATABASE_URL
  endlocal & exit /b 0
)

if not defined DB_HOST set "DB_HOST=localhost"
if not defined DB_PORT set "DB_PORT=5432"
if not defined DB_NAME set "DB_NAME=agriasset"
if not defined DB_USER set "DB_USER=postgres"

if defined DB_PASSWORD (
  set "PGPASSWORD=%DB_PASSWORD%"
  if "%QUIET%"=="0" echo [OK] Backend DB password loaded from DB_PASSWORD
  endlocal & (
    set "DB_HOST=%DB_HOST%"
    set "DB_PORT=%DB_PORT%"
    set "DB_NAME=%DB_NAME%"
    set "DB_USER=%DB_USER%"
    set "DB_PASSWORD=%DB_PASSWORD%"
    set "PGPASSWORD=%PGPASSWORD%"
    exit /b 0
  )
)

set "PGPASS_FILE=%APPDATA%\postgresql\pgpass.conf"
set "PGPASS_PASSWORD="
if exist "%PGPASS_FILE%" (
  for /f "usebackq delims=" %%P in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$pgpass = Join-Path $env:APPDATA 'postgresql\\pgpass.conf'; if (Test-Path $pgpass) { $line = Get-Content $pgpass | Where-Object { $_ -match '^(localhost|127\\.0\\.0\\.1|\\*):(5432|\\*):(agriasset|postgres|\\*):(postgres|agriasset|\\*):' } | Select-Object -First 1; if ($line) { ($line -split ':', 5)[4] } }"`) do (
    set "PGPASS_PASSWORD=%%P"
  )
)

if not defined PGPASS_PASSWORD (
  if "%QUIET%"=="0" echo [WARN] No backend DB password resolved from backend\.env, DATABASE_URL, DB_PASSWORD, or pgpass.conf.
  endlocal & exit /b 0
)

set "DB_PASSWORD=%PGPASS_PASSWORD%"
set "PGPASSWORD=%PGPASS_PASSWORD%"
if "%QUIET%"=="0" echo [OK] Backend DB password loaded from pgpass.conf
endlocal & (
  set "DB_HOST=%DB_HOST%"
  set "DB_PORT=%DB_PORT%"
  set "DB_NAME=%DB_NAME%"
  set "DB_USER=%DB_USER%"
  set "DB_PASSWORD=%DB_PASSWORD%"
  set "PGPASSWORD=%PGPASSWORD%"
  exit /b 0
)
