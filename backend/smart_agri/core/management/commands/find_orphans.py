from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import connection

class Command(BaseCommand):
    help = 'Identify tables in the database that do not have a corresponding Django model.'

    def handle(self, *args, **options):
        # 1. Get all table names defined in Models
        model_tables = set()
        for model in apps.get_models():
            model_tables.add(model._meta.db_table)

        # 2. Get all table names in the actual Database
        with connection.cursor() as cursor:
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            db_tables = set(row[0] for row in cursor.fetchall())

        # 3. Filter out known system tables
        ignored_prefixes = ('django_', 'auth_', 'spatial_ref_sys')
        
        orphans = []
        for table in db_tables:
            if table in model_tables:
                continue
            if table.startswith(ignored_prefixes):
                continue
            orphans.append(table)

        # 4. Report
        self.stdout.write(self.style.WARNING(f"\nFound {len(orphans)} orphan tables:"))
        for table in sorted(orphans):
            self.stdout.write(f" - {table}")
            
        if not orphans:
            self.stdout.write(self.style.SUCCESS("No orphan tables found! System is clean."))
