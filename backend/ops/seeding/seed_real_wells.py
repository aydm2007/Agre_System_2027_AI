"""
Seed Wells + verify Locations for ALL farms in DB.
Run: python -u seed_real_wells.py
"""
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
import django; django.setup()

from decimal import Decimal
from smart_agri.core.models import Farm, Asset, Location
from smart_agri.users.models import User
from smart_agri.accounts.models import FarmMembership

print("=== Farms in DB ===")
for f in Farm.objects.filter(deleted_at__isnull=True):
    locs = Location.objects.filter(farm=f, deleted_at__isnull=True)
    wells = Asset.objects.filter(farm=f, category='Well', deleted_at__isnull=True)
    print(f"  Farm[{f.id}] {f.name}: {locs.count()} locations, {wells.count()} wells")
    
    # Seed default location if none exist
    if locs.count() == 0:
        Location.objects.create(farm=f, name=f"موقع رئيسي - {f.name}", type="Field")
        print(f"    -> Created default location for {f.name}")
    
    # Seed default well asset if none exist
    if wells.count() == 0:
        Asset.objects.create(
            farm=f,
            name=f"بئر ارتوازي - {f.name}",
            category="Well",
            asset_type="deep_well",
            purchase_value=Decimal('10000000.00'),
            status="ACTIVE"
        )
        print(f"    -> Created default well asset for {f.name}")

print("\n=== FarmMemberships for ibrahim ===")
user = User.objects.filter(username='ibrahim').first()
if user:
    for m in FarmMembership.objects.filter(user=user):
        print(f"  Farm[{m.farm_id}] {m.farm.name} -> Role: {m.role}")
else:
    print("  User ibrahim not found!")

print("\n=== Assets (category=Well) ===")
for a in Asset.objects.filter(category='Well', deleted_at__isnull=True):
    print(f"  Asset[{a.id}] {a.name} (farm={a.farm.name}, status={a.status})")

print("\nDone!")
