#!/bin/sh
# [AGRI-GUARDIAN] V21 Production Entrypoint

set -e

echo "======================================"
echo " Starting AgriAsset V21 Backend       "
echo "======================================"

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL database..."
while ! pg_isready -d $DATABASE_URL > /dev/null 2> /dev/null; do
  sleep 2
done
echo "PostgreSQL is ready!"

# Apply migrations
echo "Applying database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Optionally create superuser if not exists
# python manage.py createsuperuser --noinput || true

# Check if we should initialize essential roles/units
if [ "$SEED_DATABASE" = "1" ]; then
    echo "Running basic essential seeders..."
    python manage.py seed_yemen_units
    python manage.py seed_roles
fi

# Start Gunicorn ASGI server
echo "Starting ASGI Server (Gunicorn + Uvicorn)..."
exec gunicorn core_project.asgi:application \
    --name agriasset_v21 \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --log-level info \
    --access-logfile - \
    --error-logfile -
