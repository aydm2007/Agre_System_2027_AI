import os
import django
from django.core.management import call_command

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

with open('migration_output.txt', 'w') as f:
    try:
        f.write("Running makemigrations...\n")
        call_command('makemigrations', 'core')
        f.write("Makemigrations complete.\n")
        
        f.write("Running migrate...\n")
        call_command('migrate')
        f.write("Migrate complete.\n")
    except Exception as e:
        f.write(f"Error: {e}\n")
