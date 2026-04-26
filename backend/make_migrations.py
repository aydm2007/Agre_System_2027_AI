import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
    from django.core.management import execute_from_command_line
    print("Running makemigrations...")
    execute_from_command_line(["manage.py", "makemigrations"])
    print("Running migrate...")
    execute_from_command_line(["manage.py", "migrate"])
    print("Migration complete.")
