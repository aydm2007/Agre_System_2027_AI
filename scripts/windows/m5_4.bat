@echo off
cd frontend
call npm ci
call npm run lint
call npm run test:ci
call npm run build
exit /b %ERRORLEVEL%
