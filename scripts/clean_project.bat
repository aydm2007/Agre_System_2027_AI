@echo off
setlocal EnableExtensions

set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

echo [Clean] Root: %ROOT%

call :safe_rmdir "%ROOT%\frontend\dist"
call :safe_rmdir "%ROOT%\frontend\playwright-report"
call :safe_rmdir "%ROOT%\frontend\test-results"
call :safe_rmdir "%ROOT%\frontend\.pw-results"
call :safe_rmdir "%ROOT%\frontend\node_modules\.vite"
call :safe_rmdir "%ROOT%\backend\logs"
call :safe_rmdir "%ROOT%\backend\media\test_uploads"
call :safe_rmdir "%ROOT%\testsprite_tests\tmp"

call :safe_del "%ROOT%\backend\db.sqlite3"
call :safe_del "%ROOT%\backend\test_db.sqlite3"
call :safe_del "%ROOT%\backend\test_sqlite.sqlite3"
call :safe_del "%ROOT%\frontend\V23_ESLINT.log"
call :safe_del "%ROOT%\frontend\V23_ESLINT.status"
call :safe_del "%ROOT%\frontend\V23_FRONTEND_GATE.log"
call :safe_del "%ROOT%\frontend\V23_NPM_INSTALL.log"
call :safe_del "%ROOT%\frontend\V24_FRONTEND_BUILD.log"
call :safe_del "%ROOT%\frontend\V24_FRONTEND_BUILD.status"
call :safe_del "%ROOT%\AGRIASSET_V23_RELEASE_GATE_REPORT.json"
call :safe_del "%ROOT%\AGRIASSET_V24_RELEASE_GATE_REPORT.json"

for /r "%ROOT%" %%F in (*.pyc *.pyo *.pyd) do del /f /q "%%F" >nul 2>&1
for /d /r "%ROOT%" %%D in (__pycache__) do if exist "%%D" rmdir /s /q "%%D" >nul 2>&1

echo [Clean] Done.
exit /b 0

:safe_rmdir
if exist %1 (
  echo [Clean] Removing %~1
  rmdir /s /q %1 >nul 2>&1
)
exit /b 0

:safe_del
if exist %1 (
  echo [Clean] Removing %~1
  del /f /q %1 >nul 2>&1
)
exit /b 0
