@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT=%~dp0"
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

set "BACKEND_DIR=%ROOT%\backend"
set "FRONTEND_DIR=%ROOT%\frontend"
set "WINDOWS_SCRIPTS=%ROOT%\scripts\windows"
set "DB_ENV_LOADER=%WINDOWS_SCRIPTS%\load_backend_db_env.cmd"

set "DO_CLEAN=0"
set "CHECK_ONLY=0"
set "DO_SEED=0"
set "DO_TEST=0"
set "DO_VERIFY=0"
set "DO_MIGRATE=0"
set "SHOW_HELP=0"
set "APP_ONLY=0"
set "DJANGO_USE_RELOAD=0"
set "FRONTEND_INSTALL_ONLY_IF_MISSING=1"

set "DEV_HOST=0.0.0.0"
set "POLL_HOST=127.0.0.1"
set "BACKEND_PORT=8000"
set "FRONTEND_PORT=5173"
set "REDIS_HOST=127.0.0.1"
set "REDIS_PORT=6379"
set "DJANGO_DEBUG_VAL=True"
set "PUBLIC_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0,195.94.24.180"
set "CELERY_BROKER_URL_VAL=redis://127.0.0.1:6379/0"
set "CELERY_RESULT_BACKEND_VAL=redis://127.0.0.1:6379/0"
set "PY_CMD="
set "NPM_CMD=npm"
set "NODE_MAJOR="
set "NPM_MAJOR="
set "REDIS_RUNTIME_MODE=external"
set "NEED_REDIS_PREFLIGHT=0"
set "IS_ADMIN=0"
set "PRIMARY_LAN_IP=127.0.0.1"
set "BACKEND_FIREWALL_RULE=AgriAsset Dev Backend 8000"
set "FRONTEND_FIREWALL_RULE=AgriAsset Dev Frontend 5173"

:parse_args
if "%~1"=="" goto :args_done
set "ARG=%~1"

if /i "%ARG%"=="clean" goto :arg_clean
if /i "%ARG%"=="check" goto :arg_check
if /i "%ARG%"=="seed" goto :arg_seed
if /i "%ARG%"=="test" goto :arg_test
if /i "%ARG%"=="verify" goto :arg_verify
if /i "%ARG%"=="migrate" goto :arg_migrate
if /i "%ARG%"=="local" goto :arg_local
if /i "%ARG%"=="public" goto :arg_public
if /i "%ARG%"=="prod" goto :arg_prod
if /i "%ARG%"=="reinstall-frontend" goto :arg_reinstall_frontend
if /i "%ARG%"=="reload" goto :arg_reload
if /i "%ARG%"=="app-only" goto :arg_app_only
if /i "%ARG%"=="help" goto :arg_help
if /i "%ARG%"=="/?" goto :arg_help

echo [ERROR] Unknown argument: %ARG%
set "SHOW_HELP=1"
shift
goto :parse_args

:arg_clean
set "DO_CLEAN=1"
shift
goto :parse_args

:arg_check
set "CHECK_ONLY=1"
shift
goto :parse_args

:arg_seed
set "DO_SEED=1"
shift
goto :parse_args

:arg_test
set "DO_TEST=1"
shift
goto :parse_args

:arg_verify
set "DO_VERIFY=1"
shift
goto :parse_args

:arg_migrate
set "DO_MIGRATE=1"
shift
goto :parse_args

:arg_local
set "DEV_HOST=127.0.0.1"
shift
goto :parse_args

:arg_public
set "DEV_HOST=0.0.0.0"
shift
goto :parse_args

:arg_prod
set "DJANGO_DEBUG_VAL=False"
shift
goto :parse_args

:arg_reinstall_frontend
set "FRONTEND_INSTALL_ONLY_IF_MISSING=0"
shift
goto :parse_args

:arg_reload
set "DJANGO_USE_RELOAD=1"
shift
goto :parse_args

:arg_app_only
set "APP_ONLY=1"
shift
goto :parse_args

:arg_help
set "SHOW_HELP=1"
shift
goto :parse_args

:args_done
if "%DO_TEST%"=="1" set "DO_VERIFY=1"
if "%SHOW_HELP%"=="1" goto :print_usage

call :ensure_layout || exit /b 1
call :resolve_python || exit /b 1
call :resolve_node_npm || exit /b 1
call :resolve_admin || exit /b 1
call :compose_allowed_hosts || exit /b 1
call :load_backend_db_env || exit /b 1

if "%DO_CLEAN%"=="1" (
  echo [Pre-Step] Running safe cleanup...
  call "%ROOT%\scripts\clean_project.bat"
  if errorlevel 1 (
    echo [ERROR] Cleanup failed. Aborting.
    exit /b 1
  )
  echo.
)

echo ==========================================
echo   AgriAsset Full Dev Stack Launcher
echo ==========================================
echo Root           : %ROOT%
echo Backend bind   : %DEV_HOST%:%BACKEND_PORT%
echo Frontend bind  : %DEV_HOST%:%FRONTEND_PORT%
if "%APP_ONLY%"=="1" (
  echo Runtime mode   : app-only
) else (
  echo Runtime mode   : full-stack
)
echo.

call :stop_repo_processes

if exist "%FRONTEND_DIR%\node_modules\.vite" (
  echo [Pre-Step] Cleaning Vite cache...
  rmdir /s /q "%FRONTEND_DIR%\node_modules\.vite" >nul 2>&1
)

call :ensure_backend_deps || exit /b 1
call :ensure_frontend_deps || exit /b 1
call :backend_preflight || exit /b 1

if "%APP_ONLY%"=="0" (
  if "%CHECK_ONLY%"=="1" set "NEED_REDIS_PREFLIGHT=1"
  if "%DO_VERIFY%"=="0" if "%DO_TEST%"=="0" set "NEED_REDIS_PREFLIGHT=1"
)
if "%NEED_REDIS_PREFLIGHT%"=="1" call :redis_preflight || exit /b 1

if "%DO_MIGRATE%"=="1" call :backend_migrate || exit /b 1
if "%DO_SEED%"=="1" call :backend_seed || exit /b 1
if "%DO_VERIFY%"=="1" call :run_verify || exit /b 1
if "%DO_TEST%"=="1" call :run_tests || exit /b 1

if "%DO_TEST%"=="0" if "%DO_VERIFY%"=="1" (
  echo [VERIFY] Verification complete. Skipping server launch.
  exit /b 0
)
if "%CHECK_ONLY%"=="1" (
  echo [CHECK] Preflight succeeded. Skipping server launch.
  exit /b 0
)

call :write_launchers || exit /b 1
if "%APP_ONLY%"=="0" if "%REDIS_RUNTIME_MODE%"=="start-local" call :start_local_redis || exit /b 1
call :ensure_public_access || exit /b 1

echo [Step 5/5] Launching local development stack...
start "AgriAsset Backend (Django)" /D "%BACKEND_DIR%" cmd.exe /d /k call "%WINDOWS_SCRIPTS%\run_backend_dev.bat"
start "AgriAsset Frontend (Vite)" /D "%FRONTEND_DIR%" cmd.exe /d /k call "%WINDOWS_SCRIPTS%\run_frontend_dev.bat"
if "%APP_ONLY%"=="0" (
  start "AgriAsset Celery Worker" /D "%BACKEND_DIR%" cmd.exe /d /k call "%WINDOWS_SCRIPTS%\run_celery_worker_dev.bat"
  start "AgriAsset Celery Beat" /D "%BACKEND_DIR%" cmd.exe /d /k call "%WINDOWS_SCRIPTS%\run_celery_beat_dev.bat"
)

call :wait_http_200 "http://%POLL_HOST%:%BACKEND_PORT%/api/health/live/" "backend livez" 45 || exit /b 1
call :wait_http_200 "http://%POLL_HOST%:%BACKEND_PORT%/api/health/ready/" "backend readyz" 45 || exit /b 1
call :wait_http_200 "http://%POLL_HOST%:%FRONTEND_PORT%/" "frontend" 45 || exit /b 1
if "%APP_ONLY%"=="0" (
  call :wait_process "celery worker" "celery" "worker" 20 || exit /b 1
  call :wait_process "celery beat" "celery" "beat" 20 || exit /b 1
)

echo.
echo ==========================================
echo   AgriAsset Dev Stack Ready
echo ==========================================
echo Backend health : http://%POLL_HOST%:%BACKEND_PORT%/api/health/ready/
echo Frontend       : http://%POLL_HOST%:%FRONTEND_PORT%/
if "%DEV_HOST%"=="0.0.0.0" (
  echo Backend LAN    : http://%PRIMARY_LAN_IP%:%BACKEND_PORT%/api/health/ready/
  echo Frontend LAN   : http://%PRIMARY_LAN_IP%:%FRONTEND_PORT%/
)
if "%APP_ONLY%"=="0" (
  echo Redis mode     : %REDIS_RUNTIME_MODE%
  echo Celery broker  : %CELERY_BROKER_URL_VAL%
)
echo Django reload  : %DJANGO_USE_RELOAD%
if "%DEV_HOST%"=="0.0.0.0" if "%IS_ADMIN%"=="0" (
  echo [WARN] Running without administrator rights. Public bind is enabled, but Windows Firewall may still block inbound internet access.
)
echo.
if "%APP_ONLY%"=="0" (
  echo Services started: backend, frontend, celery worker, celery beat
) else (
  echo Services started: backend, frontend
)
exit /b 0

:ensure_layout
if not exist "%BACKEND_DIR%\manage.py" (
  echo [ERROR] backend\manage.py not found.
  exit /b 1
)
if not exist "%FRONTEND_DIR%\package.json" (
  echo [ERROR] frontend\package.json not found.
  exit /b 1
)
if not exist "%DB_ENV_LOADER%" (
  echo [ERROR] Canonical DB env loader not found: %DB_ENV_LOADER%
  exit /b 1
)
if not exist "%WINDOWS_SCRIPTS%" mkdir "%WINDOWS_SCRIPTS%" >nul 2>&1
exit /b 0

:resolve_python
if exist "%ROOT%\.venv\Scripts\python.exe" set "PY_CMD=%ROOT%\.venv\Scripts\python.exe"
if not defined PY_CMD if exist "%ROOT%\venv\Scripts\python.exe" set "PY_CMD=%ROOT%\venv\Scripts\python.exe"
if not defined PY_CMD (
  where py >nul 2>&1 && set "PY_CMD=py -3"
)
if not defined PY_CMD (
  where python >nul 2>&1 && set "PY_CMD=python"
)
if not defined PY_CMD (
  echo [ERROR] Python not found in PATH.
  exit /b 1
)
call %PY_CMD% --version >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python command failed: %PY_CMD%
  exit /b 1
)
echo [OK] Using Python: %PY_CMD%
exit /b 0

:resolve_node_npm
where node >nul 2>&1
if errorlevel 1 (
  echo [ERROR] node not found in PATH.
  exit /b 1
)
where npm >nul 2>&1
if errorlevel 1 (
  echo [ERROR] npm not found in PATH.
  exit /b 1
)

for /f "usebackq delims=" %%V in (`powershell -NoProfile -Command "$v = (node --version).Trim().TrimStart('v'); [Console]::Out.Write($v.Split('.')[0])"`) do set "NODE_MAJOR=%%V"
for /f "usebackq delims=" %%V in (`powershell -NoProfile -Command "$v = (npm --version).Trim(); [Console]::Out.Write($v.Split('.')[0])"`) do set "NPM_MAJOR=%%V"

if not defined NODE_MAJOR (
  echo [ERROR] Failed to resolve Node major version.
  exit /b 1
)
if not defined NPM_MAJOR (
  echo [ERROR] Failed to resolve npm major version.
  exit /b 1
)
if %NODE_MAJOR% LSS 20 (
  echo [ERROR] Node.js >= 20 is required. Detected major version: %NODE_MAJOR%
  exit /b 1
)
if %NPM_MAJOR% LSS 10 (
  echo [ERROR] npm >= 10 is required. Detected major version: %NPM_MAJOR%
  exit /b 1
)
echo [OK] Using Node.js major version: %NODE_MAJOR%
echo [OK] Using npm major version: %NPM_MAJOR%
exit /b 0

:resolve_admin
net session >nul 2>&1
if not errorlevel 1 (
  set "IS_ADMIN=1"
  echo [OK] Administrator privileges detected.
) else (
  set "IS_ADMIN=0"
  echo [INFO] Running without administrator privileges.
)
exit /b 0

:compose_allowed_hosts
for /f "usebackq delims=" %%H in (`powershell -NoProfile -Command "$ips=@('localhost','127.0.0.1','0.0.0.0','195.94.24.180',$env:COMPUTERNAME); try { $ips += (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop | Where-Object { $_.IPAddress -ne '127.0.0.1' -and $_.IPAddress -notlike '169.254*' } | Select-Object -ExpandProperty IPAddress) } catch {}; ($ips | Where-Object { $_ } | Select-Object -Unique) -join ','"`) do (
  if not "%%H"=="" set "PUBLIC_ALLOWED_HOSTS=%%H"
)
for /f "usebackq delims=" %%H in (`powershell -NoProfile -Command "try { $ip=(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop | Where-Object { $_.IPAddress -ne '127.0.0.1' -and $_.IPAddress -notlike '169.254*' } | Select-Object -First 1 -ExpandProperty IPAddress); if ($ip) { $ip } else { '127.0.0.1' } } catch { '127.0.0.1' }"`) do (
  if not "%%H"=="" set "PRIMARY_LAN_IP=%%H"
)
exit /b 0

:load_backend_db_env
call "%DB_ENV_LOADER%" --quiet
if errorlevel 1 (
  echo [ERROR] Failed to preload backend DB environment through the canonical loader.
  exit /b 1
)
if not defined DATABASE_URL if not defined DB_PASSWORD if not defined PGPASSWORD if not exist "%BACKEND_DIR%\.env" (
  echo [ERROR] Backend DB environment is unresolved.
  echo [ERROR] Configure backend\.env, DATABASE_URL, DB_PASSWORD, or %%APPDATA%%\postgresql\pgpass.conf.
  exit /b 1
)
echo [OK] Backend DB environment preloaded via canonical loader.
exit /b 0

:ensure_backend_deps
echo [Step 0/5] Ensuring backend dependencies...
pushd "%BACKEND_DIR%"
call %PY_CMD% -c "import django,rest_framework,corsheaders,dotenv,celery" >nul 2>&1
if errorlevel 1 (
  echo [INFO] Backend dependencies missing or incomplete. Installing...
  call %PY_CMD% -m pip install --upgrade pip >nul 2>&1
  call %PY_CMD% -m pip install -r requirements.txt
  if errorlevel 1 (
    popd
    echo [ERROR] Backend dependency installation failed.
    exit /b 1
  )
)
echo [OK] Backend dependencies look available.
popd
exit /b 0

:ensure_frontend_deps
echo [Step 0b/5] Ensuring frontend dependencies...
pushd "%FRONTEND_DIR%"
if "%FRONTEND_INSTALL_ONLY_IF_MISSING%"=="0" (
  echo [INFO] Reinstall requested. Removing node_modules...
  if exist node_modules rmdir /s /q node_modules >nul 2>&1
)
if not exist node_modules (
  if exist package-lock.json (
    call %NPM_CMD% ci --no-audit --no-fund --loglevel=error
  ) else (
    call %NPM_CMD% install --no-audit --no-fund --loglevel=error
  )
  if errorlevel 1 (
    popd
    echo [ERROR] Frontend dependency installation failed.
    exit /b 1
  )
) else (
  echo [OK] Frontend dependencies look available.
)
popd
exit /b 0

:backend_preflight
echo [Step 1/5] Backend preflight...
pushd "%BACKEND_DIR%"
call %PY_CMD% manage.py check
if errorlevel 1 (
  popd
  echo [ERROR] Backend Django check failed.
  exit /b 1
)
call %PY_CMD% manage.py showmigrations --plan >nul
if errorlevel 1 (
  popd
  echo [ERROR] Django showmigrations --plan failed. PostgreSQL may be unavailable or misconfigured.
  exit /b 1
)
call %PY_CMD% manage.py migrate --plan >nul
if errorlevel 1 (
  popd
  echo [ERROR] Django migrate --plan failed. PostgreSQL may be unavailable or misconfigured.
  exit /b 1
)
echo [OK] PostgreSQL preflight checks passed.
popd
exit /b 0

:redis_preflight
echo [Step 2/5] Redis preflight...
call :redis_ping
if not errorlevel 1 (
  echo [OK] Redis is already reachable on %REDIS_HOST%:%REDIS_PORT%.
  set "REDIS_RUNTIME_MODE=external"
  exit /b 0
)

where redis-server >nul 2>&1
if not errorlevel 1 (
  echo [INFO] Redis is not reachable. A local redis-server will be started for this stack.
  set "REDIS_RUNTIME_MODE=start-local"
  exit /b 0
)

echo [ERROR] Redis is required for the full local stack but is not reachable.
echo [ERROR] Neither redis-cli nor a listening Redis instance was detected, and redis-server is not available in PATH.
echo [ERROR] Native/.venv mode is active. Start Redis locally on %REDIS_HOST%:%REDIS_PORT% or use the diagnostic mode: start_dev_stack.bat check app-only
exit /b 1

:redis_ping
where redis-cli >nul 2>&1
if not errorlevel 1 (
  redis-cli -h %REDIS_HOST% -p %REDIS_PORT% ping 2>nul | findstr /I /C:"PONG" >nul
  if not errorlevel 1 exit /b 0
)
powershell -NoProfile -Command "try { $client = New-Object Net.Sockets.TcpClient; $iar = $client.BeginConnect('%REDIS_HOST%', %REDIS_PORT%, $null, $null); if (-not $iar.AsyncWaitHandle.WaitOne(1500)) { $client.Close(); exit 1 }; $client.EndConnect($iar); $client.Close(); exit 0 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 exit /b 0
exit /b 1

:backend_migrate
echo [Step 3/5] Applying migrations...
pushd "%BACKEND_DIR%"
call %PY_CMD% manage.py migrate --noinput
if errorlevel 1 (
  popd
  echo [ERROR] Migration failed.
  exit /b 1
)
popd
exit /b 0

:backend_seed
echo [Step 3b/5] Running explicit seeds...
pushd "%BACKEND_DIR%"
echo [INFO] Skipping demo data seeds per user request.
call %PY_CMD% manage.py seed_yemen_units
call %PY_CMD% manage.py seed_roles
popd
exit /b 0

:run_verify
echo [Verify] Running canonical release gate...
pushd "%BACKEND_DIR%"
call %PY_CMD% manage.py verify_release_gate_v21
if errorlevel 1 (
  popd
  echo [ERROR] verify_release_gate_v21 failed.
  exit /b 1
)
popd
echo [PASS] Canonical release gate passed.
exit /b 0

:run_tests
echo [Test] Running backend test suite...
pushd "%BACKEND_DIR%"
call %PY_CMD% manage.py test --keepdb --noinput
if errorlevel 1 (
  popd
  echo [ERROR] Backend tests failed.
  exit /b 1
)
popd

echo [Test] Running frontend CI tests...
pushd "%FRONTEND_DIR%"
call %NPM_CMD% run test:ci
if errorlevel 1 (
  popd
  echo [ERROR] Frontend CI tests failed.
  exit /b 1
)
echo [Test] Running frontend build...
call %NPM_CMD% run build
if errorlevel 1 (
  popd
  echo [ERROR] Frontend build failed.
  exit /b 1
)
popd
echo [PASS] Backend tests, frontend CI tests, and build passed.
exit /b 0

:write_launchers
setlocal DisableDelayedExpansion
>"%WINDOWS_SCRIPTS%\run_backend_dev.bat" echo @echo off
>>"%WINDOWS_SCRIPTS%\run_backend_dev.bat" echo setlocal EnableExtensions
>>"%WINDOWS_SCRIPTS%\run_backend_dev.bat" echo cd /d "%BACKEND_DIR%"
>>"%WINDOWS_SCRIPTS%\run_backend_dev.bat" echo call "%DB_ENV_LOADER%" --quiet
>>"%WINDOWS_SCRIPTS%\run_backend_dev.bat" echo set "PYTHONUNBUFFERED=1"
>>"%WINDOWS_SCRIPTS%\run_backend_dev.bat" echo set "SERVER_ENV=development"
>>"%WINDOWS_SCRIPTS%\run_backend_dev.bat" echo set "DJANGO_DEBUG=%DJANGO_DEBUG_VAL%"
>>"%WINDOWS_SCRIPTS%\run_backend_dev.bat" echo set "DEBUG=%DJANGO_DEBUG_VAL%"
>>"%WINDOWS_SCRIPTS%\run_backend_dev.bat" echo set "DJANGO_ALLOWED_HOSTS=%PUBLIC_ALLOWED_HOSTS%"
>>"%WINDOWS_SCRIPTS%\run_backend_dev.bat" echo set "CELERY_BROKER_URL=%CELERY_BROKER_URL_VAL%"
>>"%WINDOWS_SCRIPTS%\run_backend_dev.bat" echo set "CELERY_RESULT_BACKEND=%CELERY_RESULT_BACKEND_VAL%"
if "%DJANGO_USE_RELOAD%"=="1" (
  >>"%WINDOWS_SCRIPTS%\run_backend_dev.bat" echo call %PY_CMD% manage.py runserver %DEV_HOST%:%BACKEND_PORT%
) else (
  >>"%WINDOWS_SCRIPTS%\run_backend_dev.bat" echo call %PY_CMD% manage.py runserver %DEV_HOST%:%BACKEND_PORT% --noreload
)

>"%WINDOWS_SCRIPTS%\run_frontend_dev.bat" echo @echo off
>>"%WINDOWS_SCRIPTS%\run_frontend_dev.bat" echo setlocal EnableExtensions
>>"%WINDOWS_SCRIPTS%\run_frontend_dev.bat" echo cd /d "%FRONTEND_DIR%"
>>"%WINDOWS_SCRIPTS%\run_frontend_dev.bat" echo call %NPM_CMD% run dev -- --host %DEV_HOST% --port %FRONTEND_PORT%

>"%WINDOWS_SCRIPTS%\run_celery_worker_dev.bat" echo @echo off
>>"%WINDOWS_SCRIPTS%\run_celery_worker_dev.bat" echo setlocal EnableExtensions
>>"%WINDOWS_SCRIPTS%\run_celery_worker_dev.bat" echo cd /d "%BACKEND_DIR%"
>>"%WINDOWS_SCRIPTS%\run_celery_worker_dev.bat" echo call "%DB_ENV_LOADER%" --quiet
>>"%WINDOWS_SCRIPTS%\run_celery_worker_dev.bat" echo set "CELERY_BROKER_URL=%CELERY_BROKER_URL_VAL%"
>>"%WINDOWS_SCRIPTS%\run_celery_worker_dev.bat" echo set "CELERY_RESULT_BACKEND=%CELERY_RESULT_BACKEND_VAL%"
>>"%WINDOWS_SCRIPTS%\run_celery_worker_dev.bat" echo call %PY_CMD% -m celery -A smart_agri worker -l info --pool=solo

>"%WINDOWS_SCRIPTS%\run_celery_beat_dev.bat" echo @echo off
>>"%WINDOWS_SCRIPTS%\run_celery_beat_dev.bat" echo setlocal EnableExtensions
>>"%WINDOWS_SCRIPTS%\run_celery_beat_dev.bat" echo cd /d "%BACKEND_DIR%"
>>"%WINDOWS_SCRIPTS%\run_celery_beat_dev.bat" echo call "%DB_ENV_LOADER%" --quiet
>>"%WINDOWS_SCRIPTS%\run_celery_beat_dev.bat" echo set "CELERY_BROKER_URL=%CELERY_BROKER_URL_VAL%"
>>"%WINDOWS_SCRIPTS%\run_celery_beat_dev.bat" echo set "CELERY_RESULT_BACKEND=%CELERY_RESULT_BACKEND_VAL%"
>>"%WINDOWS_SCRIPTS%\run_celery_beat_dev.bat" echo call %PY_CMD% -m celery -A smart_agri beat -l info

where redis-server >nul 2>&1
if not errorlevel 1 (
  >"%WINDOWS_SCRIPTS%\run_redis_dev.bat" echo @echo off
  >>"%WINDOWS_SCRIPTS%\run_redis_dev.bat" echo setlocal EnableExtensions
  >>"%WINDOWS_SCRIPTS%\run_redis_dev.bat" echo redis-server --port %REDIS_PORT%
)
endlocal
exit /b 0

:start_local_redis
if not exist "%WINDOWS_SCRIPTS%\run_redis_dev.bat" (
  echo [ERROR] Redis launcher was not created.
  exit /b 1
)
start "AgriAsset Redis" /D "%ROOT%" cmd.exe /d /k call "%WINDOWS_SCRIPTS%\run_redis_dev.bat"
call :wait_redis 20 || exit /b 1
exit /b 0

:ensure_public_access
if not "%DEV_HOST%"=="0.0.0.0" exit /b 0
if "%IS_ADMIN%"=="0" (
  echo [WARN] Public bind is enabled, but the script is not running as administrator.
  echo [WARN] If inbound internet access is blocked, rerun start_dev_stack.bat as administrator.
  exit /b 0
)
echo [Pre-Step] Ensuring Windows Firewall rules for public development access...
call :ensure_firewall_rule "%BACKEND_FIREWALL_RULE%" "%BACKEND_PORT%" || exit /b 1
call :ensure_firewall_rule "%FRONTEND_FIREWALL_RULE%" "%FRONTEND_PORT%" || exit /b 1
exit /b 0

:ensure_firewall_rule
set "RULE_NAME=%~1"
set "RULE_PORT=%~2"
netsh advfirewall firewall show rule name="%RULE_NAME%" >nul 2>&1
if not errorlevel 1 (
  echo [OK] Firewall rule already exists: %RULE_NAME%
  exit /b 0
)
netsh advfirewall firewall add rule name="%RULE_NAME%" dir=in action=allow protocol=TCP localport=%RULE_PORT% >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Failed to create Windows Firewall rule: %RULE_NAME%
  exit /b 1
)
echo [OK] Firewall rule created: %RULE_NAME%
exit /b 0

:wait_redis
set "WAIT_REDIS_SECONDS=%~1"
for /l %%S in (1,1,%WAIT_REDIS_SECONDS%) do (
  call :redis_ping
  if not errorlevel 1 (
    echo [OK] Redis is ready.
    exit /b 0
  )
  powershell -NoProfile -Command "Start-Sleep -Seconds 1" >nul 2>&1
)
echo [ERROR] Redis did not become ready on %REDIS_HOST%:%REDIS_PORT%.
exit /b 1

:wait_http_200
set "WAIT_URL=%~1"
set "WAIT_LABEL=%~2"
set "WAIT_SECONDS=%~3"
for /l %%S in (1,1,%WAIT_SECONDS%) do (
  powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; try { $r = Invoke-WebRequest -UseBasicParsing '%WAIT_URL%' -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
  if not errorlevel 1 (
    echo [OK] %WAIT_LABEL% is ready.
    exit /b 0
  )
  powershell -NoProfile -Command "Start-Sleep -Seconds 1" >nul 2>&1
)
echo [ERROR] %WAIT_LABEL% did not become ready: %WAIT_URL%
exit /b 1

:wait_process
set "PROC_LABEL=%~1"
set "PROC_MATCH_ONE=%~2"
set "PROC_MATCH_TWO=%~3"
set "PROC_WAIT_SECONDS=%~4"
for /l %%S in (1,1,%PROC_WAIT_SECONDS%) do (
  powershell -NoProfile -Command "$root=[regex]::Escape('%ROOT%'); $m1=[regex]::Escape('%PROC_MATCH_ONE%'); $m2=[regex]::Escape('%PROC_MATCH_TWO%'); $proc = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -match $root -and $_.CommandLine -match $m1 -and $_.CommandLine -match $m2 } | Select-Object -First 1; if ($proc) { exit 0 } else { exit 1 }" >nul 2>&1
  if not errorlevel 1 (
    echo [OK] %PROC_LABEL% process detected.
    exit /b 0
  )
  powershell -NoProfile -Command "Start-Sleep -Seconds 1" >nul 2>&1
)
echo [ERROR] %PROC_LABEL% process was not detected.
exit /b 1

:stop_repo_processes
call :stop_process_group "backend runserver" "manage.py" "runserver"
call :stop_process_group "frontend vite" "%FRONTEND_DIR%" "vite"
call :stop_process_group "celery worker" "celery" "worker"
call :stop_process_group "celery beat" "celery" "beat"
exit /b 0

:stop_process_group
set "STOP_LABEL=%~1"
set "STOP_MATCH_ONE=%~2"
set "STOP_MATCH_TWO=%~3"
echo [Pre-Step] Stopping %STOP_LABEL% processes in this repository...
powershell -NoProfile -Command "$root=[regex]::Escape('%ROOT%'); $m1=[regex]::Escape('%STOP_MATCH_ONE%'); $m2=[regex]::Escape('%STOP_MATCH_TWO%'); Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -match $root -and $_.CommandLine -match $m1 -and $_.CommandLine -match $m2 } | ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop } catch {} }" >nul 2>&1
exit /b 0

:print_usage
echo Usage:
echo   start_dev_stack.bat [clean] [check] [verify] [test] [migrate] [seed] [local^|public] [prod] [reload] [app-only] [reinstall-frontend]
echo.
echo Modes:
echo   default      = full local stack ^(backend + frontend + celery worker + celery beat^)
echo   app-only     = backend + frontend only ^(diagnostic mode^)
echo   check        = preflight only, no launch
echo   verify       = canonical release gate only, no launch
echo   test         = verify + backend tests + frontend CI tests + build, no launch
echo.
echo Examples:
echo   start_dev_stack.bat clean local migrate
echo   start_dev_stack.bat check
echo   start_dev_stack.bat check app-only
echo   start_dev_stack.bat local reload
echo   start_dev_stack.bat ^(double-click default: public full stack^)
exit /b 1
