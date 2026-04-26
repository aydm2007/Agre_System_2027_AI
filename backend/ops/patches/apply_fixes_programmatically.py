import os
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
import django
django.setup()

from django.core.management import call_command
from django.contrib.auth import get_user_model
from smart_agri.core.models import Farm
from smart_agri.accounts.models import FarmMembership

def run_fixes():
    try:
        print("Starting core migration...")
        call_command('migrate', 'core', interactive=False)
        print("Migration complete.")
    except Exception as e:
        print(f"Migration failed: {e}")

    try:
        print("Assigning admin farm memberships...")
        User = get_user_model()
        admin_users = User.objects.filter(is_superuser=True)
        farms = Farm.objects.all()
        count = 0
        for admin in admin_users:
            for farm in farms:
                FarmMembership.objects.get_or_create(
                    user=admin,
                    farm=farm,
                    defaults={"role": "Admin"}
                )
                count += 1
        print(f"Assigned {count} memberships.")
    except Exception as e:
        print(f"Membership assignment failed: {e}")

if __name__ == "__main__":
    run_fixes()
