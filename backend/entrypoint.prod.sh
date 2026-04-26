#!/usr/bin/env bash
set -euo pipefail

python - <<'PY'
import os, time
import psycopg2
host=os.getenv('DB_HOST','db')
port=int(os.getenv('DB_PORT','5432'))
name=os.getenv('DB_NAME')
user=os.getenv('DB_USER')
password=os.getenv('DB_PASSWORD')
if not (name and user and password):
    raise SystemExit('Missing DB_NAME/DB_USER/DB_PASSWORD in environment.')

deadline=time.time()+90
while True:
    try:
        conn=psycopg2.connect(host=host, port=port, dbname=name, user=user, password=password)
        conn.close()
        break
    except Exception:
        if time.time()>deadline:
            raise
        time.sleep(2)
PY

if [[ "${RUN_DJANGO_CHECK_DEPLOY:-1}" == "1" ]]; then
  python manage.py check --deploy
fi

if [[ "${RUN_MIGRATIONS_ON_BOOT:-1}" == "1" ]]; then
  python manage.py migrate --noinput
fi

python manage.py collectstatic --noinput

WORKERS="${GUNICORN_WORKERS:-3}"
TIMEOUT="${GUNICORN_TIMEOUT:-120}"
exec gunicorn smart_agri.wsgi:application --bind 0.0.0.0:8000 --workers "$WORKERS" --timeout "$TIMEOUT"
