import os
import django
from decimal import Decimal

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
django.setup()

from smart_agri.core.models import Farm
from smart_agri.inventory.models import Item, ItemInventory, ItemInventoryBatch

def fix_item_stock():
    print("=" * 70)
    print("Fixing Item Stock for Farm 21 (Sardood)")
    print("=" * 70)

    farm = Farm.objects.filter(id=21).first()
    if not farm:
        print("Farm 21 not found!")
        return

    # Identify Item 10
    item10 = Item.objects.filter(id=10).first()
    if not item10:
        print("Item 10 not found!")
    else:
        print(f"Item 10 identified: {item10.name} ({item10.group})")

    # Seed stock for Item 10
    items_to_seed = [10] # Add more if needed
    
    for item_id in items_to_seed:
        target_item = Item.objects.filter(id=item_id).first()
        if not target_item:
            continue
            
        # Create global inventory for the farm (location=None)
        inventory, created = ItemInventory.objects.get_or_create(
            farm=farm,
            item=target_item,
            location=None,
            crop_plan=None,
            defaults={"qty": Decimal("0.00"), "uom": target_item.uom or "unit"}
        )
        
        # Add 1000 units
        inventory.qty += Decimal("1000.00")
        inventory.save()
        print(f"  ✓ Updated inventory for {target_item.name}: {inventory.qty} {inventory.uom}")

        # Create or update a batch
        batch, b_created = ItemInventoryBatch.objects.get_or_create(
            inventory=inventory,
            batch_number="INITIAL-SEED-V21",
            defaults={"qty": Decimal("0.00")}
        )
        batch.qty += Decimal("1000.00")
        batch.save()
        print(f"  ✓ Updated batch {batch.batch_number} for {target_item.name}: {batch.qty}")

    print("\n" + "=" * 70)
    print("Inventory sync completed.")
    print("=" * 70)

if __name__ == "__main__":
    fix_item_stock()
