import os
import django
from decimal import Decimal

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
django.setup()

from smart_agri.core.models import (
    Farm, Crop, Item, FarmCrop, CropMaterial, 
    LaborRate, ItemInventory, DailyLog
)
from smart_agri.core.models.farm import Location
from django.utils import timezone

def remediate():
    farm_id = 21
    print(f"--- RUKUN REMEDIATION FOR FARM {farm_id} ---")
    
    # 1. Ensure Diesel (Item 10) Stock
    diesel_item = Item.objects.get(pk=10)
    inventory, created = ItemInventory.objects.get_or_create(
        farm_id=farm_id,
        item_id=10,
        location_id=None,
        defaults={"qty": Decimal("1000.00"), "uom": diesel_item.uom}
    )
    if not created:
        inventory.qty = Decimal("1000.00")
        inventory.save()
    print(f"  [+] Diesel stock: {inventory.qty} {inventory.uom}")

    # 2. Link Diesel to all Crops on Farm 21
    farm_crops = FarmCrop.objects.filter(farm_id=farm_id)
    for fc in farm_crops:
        cm, created = CropMaterial.objects.get_or_create(
            crop_id=fc.crop_id,
            item_id=10,
            defaults={
                "recommended_qty": Decimal("1.00"),
                "recommended_uom": diesel_item.uom,
                "notes": "Auto-linked by Rukun Remediation"
            }
        )
        status = "Created" if created else "Exists"
        print(f"  [+] CropMaterial for {fc.crop.name}: {status}")

    # 3. Ensure Labor Rate & Cost Configuration
    from smart_agri.finance.models import CostConfiguration
    
    # Cost Configuration
    config, created = CostConfiguration.objects.get_or_create(
        farm_id=farm_id,
        defaults={
            "overhead_rate_per_hectare": Decimal("100.00"),
            "currency": "SAR"
        }
    )
    if not created:
        print(f"  [+] CostConfiguration: Exists ({config.overhead_rate_per_hectare})")
    else:
        print(f"  [+] CostConfiguration: Created (100.00)")

    # Labor Rate
    rate = LaborRate.objects.filter(
        farm_id=farm_id,
        effective_date__lte=timezone.now().date(),
        deleted_at__isnull=True
    ).first()
    
    if not rate:
        rate = LaborRate.objects.create(
            farm_id=farm_id,
            role_name="عامل يومي",
            daily_rate=Decimal("50.00"),
            cost_per_hour=Decimal("6.25"),
            currency="SAR",
            effective_date=timezone.now().date()
        )
        print(f"  [+] Created labor rate: 50.00")
    else:
        print(f"  [+] Active labor rate: {rate.daily_rate}")

    # 4. Fix Database Defaults (Idempotent)
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("""
            ALTER TABLE core_activity_irrigation 
            ALTER COLUMN is_solar_powered SET DEFAULT FALSE;
            
            UPDATE core_activity_irrigation 
            SET is_solar_powered = FALSE 
            WHERE is_solar_powered IS NULL;
        """)
    print("  [+] Database schema defaults reconciled.")

    print("\n--- REMEDIATION COMPLETE ---")

if __name__ == "__main__":
    remediate()
