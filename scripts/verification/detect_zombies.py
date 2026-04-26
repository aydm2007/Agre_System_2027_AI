import os
import sys

import django
from django.db import connection
from django.db.utils import OperationalError, DatabaseError

# Setup Django environment
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../backend')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()


def _load_db_tables():
    vendor = connection.vendor
    with connection.cursor() as cursor:
        if vendor == 'postgresql':
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            return {row[0] for row in cursor.fetchall()}, vendor
        if vendor == 'sqlite':
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            return {row[0] for row in cursor.fetchall()}, vendor
        raise RuntimeError(f'Unsupported database vendor for zombie detection: {vendor}')


def detect_zombies():
    print('Detecting zombie tables...')

    try:
        db_tables, vendor = _load_db_tables()
    except (OperationalError, DatabaseError) as exc:
        print(f'BLOCKED: database unavailable for zombie detection: {exc}')
        return None
    except RuntimeError as exc:
        print(f'BLOCKED: {exc}')
        return None

    model_tables = set()
    from django.apps import apps

    for model in apps.get_models(include_auto_created=True):
        model_tables.add(model._meta.db_table)
        for m2m in model._meta.local_many_to_many:
            through = m2m.remote_field.through
            if through is not None and getattr(through._meta, 'db_table', None):
                model_tables.add(through._meta.db_table)

    zombies = []
    suspicious_patterns = {'core_iteminventory', 'core_stockmovement'}

    for table in db_tables:
        if table in model_tables:
            continue
        if table.startswith(('django_', 'auth_')):
            continue
        if vendor == 'sqlite' and table == 'sqlite_sequence':
            continue

        print(f'WARN unmanaged/zombie table found: {table}')
        zombies.append(table)

        if table in suspicious_patterns:
            print(f'CRITICAL zombie table detected: {table}')

    if not zombies:
        print('OK no zombie tables found.')
    else:
        print(f'FAIL found {len(zombies)} potential zombie tables.')

    return zombies


if __name__ == '__main__':
    zombie_tables = detect_zombies()
    if zombie_tables is None:
        raise SystemExit(2)
    if zombie_tables:
        raise SystemExit(1)
