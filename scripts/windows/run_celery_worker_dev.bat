@echo off
setlocal EnableExtensions
cd /d "C:\tools\workspace\AgriAsset_v445\backend"
call "C:\tools\workspace\AgriAsset_v445\scripts\windows\load_backend_db_env.cmd" --quiet
set "CELERY_BROKER_URL=redis://127.0.0.1:6379/0"
set "CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0"
call py -3 -m celery -A smart_agri worker -l info --pool=solo
