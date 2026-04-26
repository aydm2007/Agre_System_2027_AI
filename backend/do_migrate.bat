@echo off
setlocal
cd /d "c:\tools\workspace\AgriAsset_v44\backend"
echo Running migrations > migration_log.txt
python manage.py makemigrations core --noinput >> migration_log.txt 2>&1
python manage.py migrate --noinput >> migration_log.txt 2>&1
echo Done >> migration_log.txt
