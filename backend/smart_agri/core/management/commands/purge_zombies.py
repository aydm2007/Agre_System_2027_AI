from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Drop confirmed zombie tables.'

    def handle(self, *args, **options):
        # Explicit list of confirmed zombies to be safe
        zombies = [
            'core_treeinventory',
            'accounts_permissiontemplate_usersssions',
            'inventory_iteminventorybatch',
        ]

        with connection.cursor() as cursor:
            # check if they exist first
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            existing_tables = set(row[0] for row in cursor.fetchall())
            
            for table in zombies:
                if table in existing_tables:
                    self.stdout.write(f"Dropping zombie entity: {table}...")
                    try:
                        cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                        self.stdout.write(self.style.SUCCESS(f"Dropped TABLE {table}."))
                    except Exception as e:
                        # Maybe it is a view?
                        connection.rollback() # Important in Postgres
                        try:
                            with connection.cursor() as cursor2:
                                cursor2.execute(f"DROP VIEW IF EXISTS {table} CASCADE")
                            self.stdout.write(self.style.SUCCESS(f"Dropped VIEW {table}."))
                        except Exception as e2:
                            self.stdout.write(self.style.ERROR(f"Failed to drop {table}: {e2}"))
                else:
                    self.stdout.write(self.style.WARNING(f"Table {table} not found. Already clean?"))

        self.stdout.write(self.style.SUCCESS("Zombie purge complete."))
