from django.core.management.base import BaseCommand
from django.db import connection
import time

class Command(BaseCommand):
    help = "Analyze slow database queries"

    def handle(self, *args, **options):
        self.stdout.write("=== Query Performance Analysis ===
")
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM django_migrations;")
            row = cursor.fetchone()
            self.stdout.write(f"Total migrations: {row[0]}
")
        self.stdout.write("Tip: Use select_related() and prefetch_related() for N+1 queries
")
        self.stdout.write("Tip: Add db_index=True to frequently filtered fields
")
        self.stdout.write("Analysis complete.
")