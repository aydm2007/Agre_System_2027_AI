@echo off
setlocal EnableExtensions
cd /d "C:\tools\workspace\AgriAsset_v445\frontend"
call npm run dev -- --host 0.0.0.0 --port 5173
