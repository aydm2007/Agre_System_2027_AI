# Generated manually to fix schema mismatch for CropPlan.season column
# Made DB-agnostic for SQLite test compatibility

from django.db import migrations


class Migration(migrations.Migration):
    """
    Drop the legacy 'season' varchar column from core_cropplan.
    
    Problem:
    - The database has both 'season' (varchar NOT NULL) and 'season_id' (FK nullable)
    - Django model uses ForeignKey which maps to 'season_id'
    - The old 'season' varchar column blocks inserts due to NOT NULL constraint
    
    Solution:
    - Drop the old 'season' column
    - Keep only 'season_id' (the FK column)
    """

    dependencies = [
        ('core', '0009_create_dashboard_view'),
    ]

    def drop_legacy_column(apps, schema_editor):
        if schema_editor.connection.vendor != 'postgresql':
            # On SQLite, check if column exists first (SQLite doesn't support IF EXISTS on DROP COLUMN)
            cursor = schema_editor.connection.cursor()
            cursor.execute("PRAGMA table_info(core_cropplan);")
            columns = [row[1] for row in cursor.fetchall()]
            # SQLite < 3.35 doesn't support DROP COLUMN at all. Just skip.
            # For testing purposes, we assume the model is correct and skip.
            return
        else:
            schema_editor.execute('ALTER TABLE core_cropplan DROP COLUMN IF EXISTS season;')

    def add_legacy_column(apps, schema_editor):
        if schema_editor.connection.vendor != 'postgresql':
            return
        schema_editor.execute('ALTER TABLE core_cropplan ADD COLUMN season VARCHAR(100) NULL;')

    operations = [
        migrations.RunPython(drop_legacy_column, add_legacy_column),
    ]
