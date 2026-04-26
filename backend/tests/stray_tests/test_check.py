import sys
from django.core.management import execute_from_command_line
import os

if __name__ == "__main__":
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
    execute_from_command_line(['manage.py', 'check'])
