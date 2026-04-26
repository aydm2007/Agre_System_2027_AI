import pytest
import django
from django.db import connection

@pytest.mark.django_db
def test_detect_zombies():
    print('--- DETECT ZOMBIES START ---')
    with connection.cursor() as cursor:
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        db_tables = {row[0] for row in cursor.fetchall()}

    model_tables = set()
    from django.apps import apps
    for model in apps.get_models(include_auto_created=True):
        model_tables.add(model._meta.db_table)
        for m2m in model._meta.local_many_to_many:
            through = m2m.remote_field.through
            if through is not None and getattr(through._meta, 'db_table', None):
                model_tables.add(through._meta.db_table)

    zombies = []
    suspicious_patterns = ['core_iteminventory', 'core_stockmovement']
    for table in db_tables:
        if table in model_tables:
            continue
        if table.startswith('django_') or table.startswith('auth_'):
            continue
        print(f'WARN unmanaged/zombie table found: {table}')
        zombies.append(table)
    
    assert not zombies, f"Found zombie tables: {zombies}"
    print('--- DETECT ZOMBIES END ---')
