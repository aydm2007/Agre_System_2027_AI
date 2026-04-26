import os
import django
import sys

# Setup Django Environment
sys.path.append(r'c:\tools\workspace\Agre_ERP_2027-main\backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from smart_agri.core.models import Farm, Plot, Crop, CropCycle, Task, Activity
from smart_agri.core.models.assets import Asset

def seed_data():
    print("Seeding Test Data...")
    
    # 1. Get Farm
    farm = Farm.objects.filter(name__contains="سردود").first()
    if not farm:
        print("Error: Sardud Farm not found!")
        return
    print(f"Found Farm: {farm.name}")

    # 2. Ensure Asset (Well/Center)
    asset, _ = Asset.objects.get_or_create(
        name="محوري 1",
        farm=farm,
        defaults={'type': 'machinery', 'status': 'active'}
    )

    # 3. Ensure Crop
    crop, created = Crop.objects.get_or_create(
        name="برسيم",
        farm=farm,
        defaults={'type': 'seasonal', 'crop_season': 'winter'}
    )
    print(f"Crop 'Berseem': {'Created' if created else 'Exists'}")

    # 4. Ensure Cycle
    cycle, _ = CropCycle.objects.get_or_create(
        name="موسم 2025",
        crop=crop,
        season="winter",
        year=2025,
        defaults={'status': 'active', 'start_date': '2025-01-01'}
    )

    # 5. Ensure Task (Service)
    task, created = Task.objects.get_or_create(
        name="تسميد",
        crop=crop,
        defaults={'is_operational': True, 'rate_per_unit': 10.0}
    )
    print(f"Task 'Fertilizing': {'Created' if created else 'Exists'}")
    
    # 6. Ensure Plot
    plot, _ = Plot.objects.get_or_create(
        name="مربع 1",
        farm=farm,
        defaults={'area': 10.0, 'location_data': {}}
    )
    
    print("Seeding Complete. UI should now have this data.")

if __name__ == '__main__':
    seed_data()
