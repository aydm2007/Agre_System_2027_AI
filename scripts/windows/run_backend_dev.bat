@echo off
setlocal EnableExtensions
cd /d "C:\tools\workspace\AgriAsset_v445\backend"
call "C:\tools\workspace\AgriAsset_v445\scripts\windows\load_backend_db_env.cmd" --quiet
set "PYTHONUNBUFFERED=1"
set "SERVER_ENV=development"
set "DJANGO_DEBUG=True"
set "DEBUG=True"
set "DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0,195.94.24.180,SULTANYAHYA,192.168.4.182"
set "CELERY_BROKER_URL=redis://127.0.0.1:6379/0"
set "CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0"
call py -3 manage.py runserver 0.0.0.0:8000 --noreload
