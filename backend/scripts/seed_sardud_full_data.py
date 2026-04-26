
import os
import sys
import django
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.db import transaction

# Setup Django Environment
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
django.setup()

from smart_agri.core.models import (
    Farm, Location, Crop, CropVariety, CropProduct, DailyLog, Activity, 
    Task, Asset, Unit, HarvestActivity, ActivityHarvest, ActivityIrrigation
)
from smart_agri.inventory.models import Item, ItemInventory
from smart_agri.sales.models import SalesInvoice, SalesInvoiceItem, Customer
from django.contrib.auth import get_user_model

User = get_user_model()

def seed_sardud():
    print("🌱 Seeding Sardud Farm Data...")
    
    # 1. Get User & Farm
    admin_user = User.objects.filter(username='ibrahim').first() or User.objects.first()
    
    # Try getting Sardud by ID or Name
    sardud = Farm.objects.filter(name__icontains="Sardud").first()
    if not sardud:
        sardud = Farm.objects.filter(pk=2).first()
    
    if not sardud:
        print("⚠️ Sardud Farm not found! Creating it...")
        sardud = Farm.objects.create(name="Sardud Farm", region="Tihama", is_active=True)
    else:
        print(f"✅ Found Farm: {sardud.name} (ID: {sardud.id})")

    # 2. Master Data: Locations & Assets
    location, _ = Location.objects.get_or_create(
        farm=sardud, name="Block A - Mango", 
        defaults={"type": "Orchard", "code": "BLK-A-MANGO"} # Removed 'area', added valid fields
    )
    
    well, _ = Asset.objects.get_or_create(
        farm=sardud, name="Main Well #1", 
        defaults={"asset_type": "Well", "status": "Operational"}
    )
    
    # 3. Master Data: Crops
    # Perennial: Mango
    mango, _ = Crop.objects.get_or_create(
        name="Mango", 
        defaults={"is_perennial": True, "mode": "Open"}
    )
    mango_variety, _ = CropVariety.objects.get_or_create(crop=mango, name="Taimour")

    # Annual: Tomato
    tomato, _ = Crop.objects.get_or_create(
        name="Tomato", 
        defaults={"is_perennial": False, "mode": "Open"}
    )
    tomato_variety, _ = CropVariety.objects.get_or_create(crop=tomato, name="Local Red")

    # 4. Master Data: Products (Farm Scoped!)
    # Mango Box
    mango_item, _ = Item.objects.get_or_create(
        name="Mango Box 5kg", 
        defaults={"group": "Produce", "uom": "Box"}
    )
    mango_product, _ = CropProduct.objects.get_or_create(
        crop=mango, 
        farm=sardud,
        name="Mango Premium Box",
        defaults={
            "item": mango_item, # Will use fallback logic in save if missing, but we provide it
            "pack_size": 5.0,
            "pack_uom": "kg",
            "is_primary": True
        }
    )
    # Ensure item link is set if created previously
    if mango_product.item != mango_item:
        mango_product.item = mango_item
        mango_product.save()

    # Tomato Basket
    tomato_item, _ = Item.objects.get_or_create(
        name="Tomato Basket 20kg", 
        defaults={"group": "Produce", "uom": "Basket"}
    )
    tomato_product, _ = CropProduct.objects.get_or_create(
        crop=tomato, 
        farm=sardud,
        name="Tomato Standard Basket",
        defaults={
            "item": tomato_item,
            "pack_size": 20.0,
            "pack_uom": "kg",
            "is_primary": True
        }
    )
    if tomato_product.item != tomato_item:
        tomato_product.item = tomato_item
        tomato_product.save()

    # 5. Inventory Initialization
    for item in [mango_item, tomato_item]:
        inv, created = ItemInventory.objects.get_or_create(
            farm=sardud, item=item,
            defaults={"quantity": 0, "value": 0}
        )
        inv.quantity += 100
        inv.save()

    # 6. Operations: Tasks (Crop Specific)
    mango_harvest_task, _ = Task.objects.get_or_create(
        name="Harvest Mango", 
        crop=mango,
        defaults={"is_harvest_task": True, "stage": "Harvest"}
    )
    
    tomato_harvest_task, _ = Task.objects.get_or_create(
        name="Harvest Tomato", 
        crop=tomato,
        defaults={"is_harvest_task": True, "stage": "Harvest"}
    )
    
    tomato_irrigation_task, _ = Task.objects.get_or_create(
        name="Irrigation Tomato", 
        crop=tomato,
        defaults={"is_harvest_task": False, "requires_well": True, "stage": "Growth"}
    )

    # 7. Operations: Daily Logs
    today = timezone.localdate()
    
    with transaction.atomic():
        # Log 1: Irrigation (2 days ago)
        log1, _ = DailyLog.objects.get_or_create( # Avoid dupe if re-run
            farm=sardud, 
            log_date=today - timedelta(days=2),
            defaults={"created_by": admin_user}
        )
        
        # Check if activity exists to avoid key unique violation if re-run
        if not Activity.objects.filter(log=log1, task=tomato_irrigation_task).exists():
            act1 = Activity.objects.create(
                log=log1,
                task=tomato_irrigation_task,
                crop=tomato,
                location=location,
                asset=well,
                well_asset=well, # Legacy field
                created_by=admin_user,
                data={"water_volume": "150.00", "water_uom": "m3"}
            )
            ActivityIrrigation.objects.create(
                activity=act1,
                water_volume=Decimal("150.00"),
                uom="m3",
                well_asset=well
            )
            print("  - Log 1: Irrigation Created")

        # Log 2: Harvest (Yesterday) - Mango
        log2, _ = DailyLog.objects.get_or_create(
            farm=sardud, log_date=today - timedelta(days=1),
            defaults={"created_by": admin_user}
        )
        
        if not Activity.objects.filter(log=log2, task=mango_harvest_task).exists():
            act2 = Activity.objects.create(
                log=log2,
                task=mango_harvest_task,
                crop=mango,
                crop_variety=mango_variety,
                location=location,
                created_by=admin_user,
                product=mango_product,
                data={"harvest_quantity": "50"}
            )
            ActivityHarvest.objects.create(
                activity=act2,
                harvest_quantity=Decimal("50.00"),
                uom="Box",
                batch_number=f"BATCH-{today.strftime('%Y%m%d')}-MANGO",
                product_id=mango_product.id
            )
            print("  - Log 2: Mango Harvest Created")

        # Log 3: Harvest (Today) - Tomato
        log3, _ = DailyLog.objects.get_or_create(
            farm=sardud, log_date=today,
            defaults={"created_by": admin_user}
        )
        
        if not Activity.objects.filter(log=log3, task=tomato_harvest_task).exists():
            act3 = Activity.objects.create(
                log=log3,
                task=tomato_harvest_task,
                crop=tomato,
                crop_variety=tomato_variety,
                location=location,
                created_by=admin_user,
                product=tomato_product,
                data={"harvest_quantity": "20"}
            )
            ActivityHarvest.objects.create(
                activity=act3,
                harvest_quantity=Decimal("20.00"),
                uom="Basket",
                product_id=tomato_product.id
            )
            print("  - Log 3: Tomato Harvest Created")

    # 8. Sales: Customers & Invoices
    customer, _ = Customer.objects.get_or_create(
        name="Al-Khair Wholesale Market",
        defaults={"customer_type": Customer.TYPE_WHOLESALER, "phone": "777000000"}
    )
    
    # Invoice 1: Sales of Mango & Tomato
    # Check if invoice exists for this day/customer to avoid duplicates
    if not SalesInvoice.objects.filter(farm=sardud, invoice_date=today, customer=customer).exists():
        with transaction.atomic():
            invoice = SalesInvoice.objects.create(
                farm=sardud,
                customer=customer,
                invoice_date=today,
                status=SalesInvoice.STATUS_APPROVED,
                created_by=admin_user,
                total_amount=Decimal("0"), 
                tax_amount=Decimal("0"),
                net_amount=Decimal("0")
            )
            
            # Item 1: Mango
            item1 = SalesInvoiceItem.objects.create(
                invoice=invoice,
                item=mango_item,
                qty=Decimal("10"),
                unit_price=Decimal("5000.00"), 
                total=Decimal("50000.00")
            )
            
            # Item 2: Tomato
            item2 = SalesInvoiceItem.objects.create(
                invoice=invoice,
                item=tomato_item,
                qty=Decimal("5"),
                unit_price=Decimal("8000.00"), 
                total=Decimal("40000.00")
            )
            
            invoice.total_amount = item1.total + item2.total
            invoice.net_amount = invoice.total_amount 
            invoice.save()
            
            print(f"✅ Created Sales Invoice #{invoice.id} for {customer.name} - Total: {invoice.total_amount}")
    else:
        print("ℹ️ Sales Invoice already exists for today.")

    print("\n🎉 Seeding Complete! Sardud Farm is ready.")

if __name__ == "__main__":
    try:
        seed_sardud()
    except Exception as e:
        print(f"❌ Error seeding data: {e}")
        import traceback
        traceback.print_exc()
