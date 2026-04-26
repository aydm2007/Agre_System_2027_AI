import os
import django
import sys
from django.db.models import Sum

# Setup Django
sys.path.append(r'C:\tools\workspace\AgriAsset_v44_test\backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from smart_agri.inventory.models import ItemInventory, ItemInventoryBatch

def run_inventory_audit():
    print("💎 [SOVEREIGN AUDIT] Starting Phase 2: Inventory Arithmetic Check...")
    
    mismatches = 0
    total_checked = 0
    
    inventories = ItemInventory.objects.all()
    for inv in inventories:
        total_checked += 1
        # Calculate sum from batches
        batch_sum = ItemInventoryBatch.objects.filter(inventory=inv).aggregate(total=Sum('qty'))['total'] or 0
        
        if inv.qty != batch_sum:
            print(f"🚨 [MISMATCH] Inventory ID {inv.id} ({inv.item.name}): Master={inv.qty}, Batches={batch_sum}")
            mismatches += 1
            
            # AUTO-REPAIR: Sync Master with Batches (Batches are the source of truth)
            inv.qty = batch_sum
            inv.save()
            print(f"🛠️ [FIXED] Synchronized Master qty to {batch_sum}.")

    print("\n📊 [INVENTORY AUDIT SUMMARY]")
    print(f"---------------------------------")
    print(f"Records Checked: {total_checked}")
    print(f"Mismatches Fixed: {mismatches}")
    print(f"Status: ✅ CONSISTENT")
    print(f"---------------------------------\n")

if __name__ == "__main__":
    run_inventory_audit()
