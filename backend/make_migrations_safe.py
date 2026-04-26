import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
    import django
    django.setup()
    
    from django.core.management import execute_from_command_line
    
    print("Running makemigrations core...")
    execute_from_command_line(["manage.py", "makemigrations", "core", "--noinput"])
    
    print("Running migrate core...")
    execute_from_command_line(["manage.py", "migrate", "core", "--noinput"])
    
    print("All done!")
