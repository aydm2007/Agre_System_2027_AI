@echo off
SET "JAVA_HOME=C:\Program Files (x86)\Android\openjdk\jdk-17.0.14"
SET "_JAVA_OPTIONS=-Duser.language=en -Duser.country=US"
echo [AgriAsset] Starting Universal Production Build (Web, Android, Windows)...
cd /d "%~dp0.."

echo [1/3] Building Web Platform...
call flutter build web --release

echo [2/3] Building Android APK (Split per ABI)...
call flutter build apk --release --split-per-abi

echo [3/3] Building Windows Desktop...
call flutter build windows --release

echo [✓] All Build Artifacts Generated!
pause
