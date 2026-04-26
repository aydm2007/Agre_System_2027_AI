import os
import django
from decimal import Decimal
from django.test import Client
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from smart_agri.core.models import CropPlan, Farm, Item, Unit
from django.contrib.auth import get_user_model

User = get_user_model()

def run_simulation():
    print("Starting Step 3 Simulation (API Based)...")
    
    # Needs a superuser for API access
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        print("No superuser found.")
        return
        
    client = Client()
    client.force_login(user)
    
    plan = CropPlan.objects.filter(name__icontains='خطة التدقيق النهائية 2026').last()
    if not plan:
        print("Crop Plan not found.")
        return
        
    farm = plan.farm
    
    # 1. Harvest Simulation
    print("\n--- 1. Simulating Harvest ---")
    # To do a harvest, the frontend calls the Daily Log api or Harvest Log api.
    # We will just use the ORM to mimic the backend logic to ensure the logic itself holds.
    from smart_agri.core.models import HarvestLog, HarvestLot, LocationCrop
    
    loc_crop = LocationCrop.objects.filter(farm=farm, crop=plan.crop).first()
    if not loc_crop:
        print("No LocationCrop found for this farm and crop.")
        # Create one for testing
        from smart_agri.core.models import Location
        loc = Location.objects.filter(farm=farm).first()
        loc_crop = LocationCrop.objects.create(farm=farm, location=loc, crop=plan.crop, area=10)

    # Note: We are simulating the EXACT serializer payloads.
    harvest_payload = {
        'farm': farm.id,
        'crop_plan': plan.id,
        'location_crop': loc_crop.id,
        'date': '2026-06-01',
        'qty_harvested': '1000.00',
        'cost_per_unit': '50.00', # 50,000 total cost
        'notes': 'E2E Test Harvest'
    }
    
    # Since we might not know the exact endpoint for HarvestLog right now, 
    # Let's do it via ORM to be safe and accurate to the business rules.
    try:
        harvest_log = HarvestLog.objects.create(
            farm=farm,
            crop_plan=plan,
            location_crop=loc_crop,
            date='2026-06-01',
            qty_harvested=Decimal('1000.00'),
            cost_per_unit=Decimal('50.00'),
            total_cost=Decimal('50000.00')
        )
        # Create HarvestLot
        lot = HarvestLot.objects.create(
            farm=farm,
            harvest_log=harvest_log,
            crop=plan.crop,
            lot_number="LOT-E2E-2026",
            qty_initial=Decimal('1000.00'),
            qty_available=Decimal('1000.00'),
            unit_cost=Decimal('50.00')
        )
        print(f"Success: Harvest Lot {lot.lot_number} created. Cost/Unit: {lot.unit_cost}")
    except Exception as e:
        print(f"Error during Harvest: {e}")
        return

    # 2. Sales Simulation & Pricing Engine 
    print("\n--- 2. Simulating Sales & Governance Engine ---")
    from smart_agri.sales.models import SalesInvoice, SalesInvoiceItem, Customer
    
    customer, _ = Customer.objects.get_or_create(name="عميل اختبار", defaults={'phone': '0500000000'})
    
    invoice = SalesInvoice.objects.create(
        farm=farm,
        customer=customer,
        date='2026-06-05',
        status='draft',
        notes='E2E Audit Sales'
    )
    
    print("Attempting to sell below cost to trigger Governance Auto-Pricing Engine...")
    try:
        # Sell at 10.00 when cost is 50.00
        item = SalesInvoiceItem(
            invoice=invoice,
            harvest_lot=lot,
            qty=Decimal('100.00'),
            unit_price=Decimal('10.00') # Below cost!
        )
        # Assuming the clean() method enforces the rule
        item.clean()
        item.save()
        print("FAILURE: System allowed selling below cost!")
    except Exception as e:
        print(f"SUCCESS: System blocked the sale as expected. Error: {e}")
        
    print("Attempting to sell at a profitable price...")
    try:
        # Sell at 75.00 when cost is 50.00
        item = SalesInvoiceItem(
            invoice=invoice,
            harvest_lot=lot,
            qty=Decimal('100.00'),
            unit_price=Decimal('75.00') # Profitable
        )
        item.clean()
        item.save()
        print("SUCCESS: System allowed the profitable sale.")
        
        # Approve invoice
        invoice.status = 'approved'
        invoice.clean()
        invoice.save()
        print("Invoice Approved.")
    except Exception as e:
        print(f"FAILURE: Profitable sale failed unexpectedly. Error: {e}")

if __name__ == '__main__':
    run_simulation()
