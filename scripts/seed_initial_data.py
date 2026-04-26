import os
import sys
import django
from decimal import Decimal
from datetime import date

# Setup Django
sys.path.append(os.path.join(os.getcwd(), 'backend'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
django.setup()

from django.contrib.auth import get_user_model
from smart_agri.core.models.farm import Farm, Location, Asset
from smart_agri.core.models.crop import Crop
from smart_agri.core.models.planning import Season
from smart_agri.inventory.models import Unit
from smart_agri.accounts.models import FarmMembership

User = get_user_model()

def seed():
    print("🌱 Seeding Initial Data for AgriAsset 2025...")

    # 1. Admin User (Double check/Create)
    try:
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', '123456')
            print("✅ Created superuser 'admin' with password '123456'")
        else:
            u = User.objects.get(username='admin')
            u.set_password('123456')
            u.save()
            print("✅ Updated 'admin' password to '123456'")
        admin = User.objects.get(username='admin')
    except Exception as e:
        print(f"❌ Error with admin user: {e}")
        return

    # 2. Units (Master Data)
    units_data = [
        ("kg", "Kilogram", "kg", Unit.CATEGORY_MASS),
        ("ton", "Ton", "t", Unit.CATEGORY_MASS),
        ("l", "Liter", "L", Unit.CATEGORY_VOLUME),
        ("ha", "Hectare", "ha", Unit.CATEGORY_AREA),
        ("acre", "Acre", "ac", Unit.CATEGORY_AREA),
        ("pcs", "Pieces", "pcs", Unit.CATEGORY_COUNT),
        ("hr", "Hour", "hr", Unit.CATEGORY_TIME),
    ]
    
    for code, name, sym, cat in units_data:
        u, created = Unit.objects.get_or_create(
            code=code,
            defaults={'name': name, 'symbol': sym, 'category': cat}
        )
        if created: print(f"   + Created Unit: {name}")

    # 3. Crops (Master Data)
    crops_data = [
        ("Mango", "Protected", True),   # Perennial
        ("Banana", "Open", True),       # Perennial
        ("Wheat", "Open", False),       # Annual
        ("Tomato", "Protected", False),
        ("Potato", "Open", False),
    ]

    for name, mode, is_perennial in crops_data:
        c, created = Crop.objects.get_or_create(
            name=name,
            mode=mode,
            defaults={'is_perennial': is_perennial}
        )
        if created: print(f"   + Created Crop: {name}")

    # 4. Seasons
    seasons_data = [
        ("Winter 2024", date(2024, 10, 1), date(2025, 3, 31)),
        ("Summer 2025", date(2025, 4, 1), date(2025, 9, 30)),
    ]

    for name, start, end in seasons_data:
        s, created = Season.objects.get_or_create(
            name=name,
            defaults={'start_date': start, 'end_date': end, 'is_active': True}
        )
        if created: print(f"   + Created Season: {name}")

    # 5. Farms & Users
    farms_data = [
        ("Sardud", "sardud", "Sardud Valley", Farm.ZAKAT_TITHE, "manager_sardud"),
        ("Al-Jarubah", "al-jarubah", "Jarubah Plain", Farm.ZAKAT_HALF_TITHE, "manager_al_jarubah"),
    ]

    for name, slug, region, zakat, mgr_user in farms_data:
        farm, f_created = Farm.objects.get_or_create(
            slug=slug,
            defaults={'name': name, 'region': region, 'zakat_rule': zakat}
        )
        if f_created: print(f"   + Created Farm: {name}")

        # Link Admin
        FarmMembership.objects.get_or_create(
            user=admin,
            farm=farm,
            defaults={'role': 'Admin'}
        )

        # Create & Link Manager
        try:
            mgr, created = User.objects.get_or_create(username=mgr_user)
            if created:
                mgr.set_password('123')
                # Make them active and staff so they can login if needed, or just active
                mgr.is_active = True
                mgr.is_staff = True # Optional, depending on permission policy
                mgr.save()
                print(f"     -> Created Manager User: {mgr_user} (Pass: 123)")
            
            FarmMembership.objects.get_or_create(
                user=mgr,
                farm=farm,
                defaults={'role': 'Manager'}
            )
            print(f"     -> Assigned {mgr_user} to {name}")
        except Exception as e:
            print(f"     ! Error with manager {mgr_user}: {e}")

        # Locations
        locs = ["Field A", "Field B", "Greenhouse 1"]
        for loc_name in locs:
            l, l_created = Location.objects.get_or_create(
                farm=farm,
                name=loc_name,
                defaults={'type': 'Field' if 'Field' in loc_name else 'Protected'}
            )

        # Assets
        assets = [
            ("Well 1", "Well"),
            ("Main Tractor", "Machinery"),
            ("Irrigation Pump", "Irrigation")
        ]
        for a_name, a_cat in assets:
            a, a_created = Asset.objects.get_or_create(
                farm=farm,
                name=a_name,
                defaults={
                    'category': a_cat, 
                    'purchase_value': 10000, 
                    'status': 'active'
                }
            )

    print("\n" + "="*40)
    print("📢 CREDENTIALS (تم إنشاء المستخدمين):")
    print("="*40)
    print(f"1. System Admin:      admin              / 123456")
    print(f"2. Sardud Manager:    manager_sardud     / 123")
    print(f"3. Jarubah Manager:   manager_al_jarubah / 123")
    print("="*40 + "\n")
    print("✅ Seeding Complete!")

if __name__ == "__main__":
    seed()
