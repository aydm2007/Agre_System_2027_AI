from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Drop confirmed residual zombie tables."

    ZOMBIE_TABLES = (
        "system_logs",
        "audit_logs",
        "users",
        "workflow_state",
    )

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            existing_tables = {row[0] for row in cursor.fetchall()}

            for table in self.ZOMBIE_TABLES:
                if table in existing_tables:
                    self.stdout.write(f"Dropping zombie entity: {table}...")
                    cursor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')
                    self.stdout.write(self.style.SUCCESS(f"Dropped TABLE {table}."))
                else:
                    self.stdout.write(self.style.WARNING(f"Table {table} not found. Already clean?"))

        self.stdout.write(self.style.SUCCESS("Zombie purge complete."))
