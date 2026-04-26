import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from django.contrib.auth.models import Group, Permission
from smart_agri.accounts.models import FarmGovernanceProfile, RaciTemplate, RoleDelegation
from smart_agri.accounts.models import FarmMembership


def run_inspection():
    print("--- GROUPS ---")
    groups = Group.objects.all()
    for g in groups:
        print(f"Group: {g.name} (Permissions count: {g.permissions.count()})")

    print("\n--- PERMISSION ARABIC COLUMN ---")
    has_col = hasattr(Permission.objects.first(), 'name_arabic')
    print(f"Has name_arabic column: {has_col}")
    
    if has_col:
        print("\n--- PERMISSION SAMPLES ---")
        perms = Permission.objects.filter(content_type__app_label='core')[:5]
        for p in perms:
            print(f"{p.codename} | {p.name} | {getattr(p, 'name_arabic', 'None')}")

    print("\n--- GOVERNANCE PROFILES ---")
    for gp in FarmGovernanceProfile.objects.all()[:3]:
        print(f"Farm: {gp.farm.name}, Strict: {gp.is_strict}, Default Role: {gp.default_role}")
        
    print("\n--- RACI TEMPLATES ---")
    for r in RaciTemplate.objects.all()[:5]:
        print(f"Template: {r.name}, Role: {r.role}, Applies to Tier: {r.farm_tier}")

if __name__ == '__main__':
    run_inspection()
