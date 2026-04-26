from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import connection
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Deletes orphan tables that do not have a corresponding Django model.'

    def handle(self, *args, **options):
        # 1. Get all model table names
        model_tables = set()
        for model in apps.get_models():
            model_tables.add(model._meta.db_table)
            # Include M2M tables that are auto-generated
            for field in model._meta.local_many_to_many:
                if field.remote_field.through:
                     model_tables.add(field.remote_field.through._meta.db_table)

        # 2. Get all database tables
        all_tables = set(connection.introspection.table_names())

        # 3. Find orphans
        # Whitelist standard tables that might not be in models or essential
        whitelist = {'django_migrations', 'sqlite_sequence', 'geometry_columns', 'spatial_ref_sys'}
        
        # Filter out model tables
        orphans = {t for t in all_tables if t not in model_tables and t not in whitelist}

        if not orphans:
            self.stdout.write(self.style.SUCCESS("No orphan tables found."))
            return

        self.stdout.write(self.style.WARNING(f"Found {len(orphans)} orphan tables: {', '.join(orphans)}"))
        
        # 4. Drop
        with connection.cursor() as cursor:
            for table in orphans:
                self.stdout.write(f"Dropping table {table}...")
                # Use double quotes for safety
                try:
                    cursor.execute(f'DROP TABLE "{table}" CASCADE')
                except Exception as exc:
                     # Fallback for sqlite which might not like CASCADE
                     logger.warning("CASCADE drop failed for %s, trying without: %s", table, exc)
                     cursor.execute(f'DROP TABLE "{table}"')
        
        self.stdout.write(self.style.SUCCESS("Orphan tables cleaned."))

