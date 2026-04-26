import os
import sys

def log(msg):
    with open('step3_log.txt', 'a', encoding='utf-8') as f:
        f.write(str(msg) + "\n")

log("Initializing Step 3 E2E Django Environment...")

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
import django
django.setup()

from smart_agri.core.models import CropPlan, Location, DailyLog, Activity, ActivityHarvest, HarvestLot
from smart_agri.sales.models import SalesInvoice, SalesInvoiceItem, Customer
from decimal import Decimal
from django.utils import timezone

def run():
    open('step3_log.txt', 'w').close() # Clear file
    log("\n--- [Audit Step 3: Harvest and Sales Simulation] ---")
    
    plan = CropPlan.objects.filter(name__icontains='خطة التدقيق النهائية 2026').last()
    if not plan:
        log("❌ Crop Plan 'خطة التدقيق النهائية 2026' not found. Cannot proceed.")
        return
        
    farm = plan.farm
    log(f"✅ Found Crop Plan for Farm: {farm.name}")
    
    today = timezone.now().date()
    
    # 1. Harvest Simulation
    log("\n[Phase A] Simulating Harvest Operation...")
    loc = Location.objects.filter(farm=farm).first()
    if not loc:
         log("❌ Failed to find any location for farm.")
         return

    try:
        daily_log = DailyLog.objects.create(
            farm=farm,
            log_date=today,
            status='APPROVED'
        )
        log(f"✅ DailyLog created successfully with date {today}.")
        
        activity = Activity.objects.create(
            log=daily_log,
            crop_plan=plan,
            crop=plan.crop,
            location=loc,
            data={"note": "E2E Harvest Simulation"}
        )

        lot, created = HarvestLot.objects.get_or_create(
            farm=farm,
            crop=plan.crop,
            crop_plan=plan,
            location=loc,
            harvest_date=today,
            defaults={
                'quantity': Decimal('1000.00'),
                'uom': 'kg',
                'grade': 'First'
            }
        )
        
        if not created:
             lot.quantity += Decimal('1000.00')
             lot.save()

        log(f"✅ Harvest Lot generated/updated. Current quantity: {lot.quantity} kg")

        harvest_activity = ActivityHarvest.objects.create(
            activity=activity,
            harvest_quantity=Decimal('1000.00'),
            uom='kg',
            lot=lot
        )
        
        log("✅ ActivityHarvest created successfully.")
        
    except Exception as e:
        log(f"❌ Error during Harvest Creation: {e}")
        import traceback
        log(traceback.format_exc())
        return

    # 2. Sales Simulation
    log("\n[Phase B] Simulating Sales & Auto-Pricing Governance Engine...")
    customer, _ = Customer.objects.get_or_create(name="عميل اختبار", phone="0500000000")
    
    invoice = SalesInvoice.objects.create(
        farm=farm,
        customer=customer,
        date=today,
        status='draft',
        notes='E2E Audit Sales'
    )
    
    log("Testing Rule: Preventing sales below cost (Assumed minimum, testing interceptor...)")
    try:
        item = SalesInvoiceItem(
            invoice=invoice,
            harvest_lot=lot,
            qty=Decimal('100.00'),
            unit_price=Decimal('1.00') # Absurdly low
        )
        item.clean()
        item.save()
        log("❌ FAILURE: System allowed sale infinitely below standard price!")
    except Exception as e:
        log(f"✅ SUCCESS: System intercepted the sale! Governance Validation Error: {e}")
        
    log("\nTesting Rule: Allowing profitable/standard sale (Price=5000.00)")
    try:
        item = SalesInvoiceItem(
            invoice=invoice,
            harvest_lot=lot,
            qty=Decimal('100.00'),
            unit_price=Decimal('5000.00')
        )
        item.clean()
        item.save()
        
        invoice.status = 'approved'
        invoice.clean()
        invoice.save()
        log("✅ SUCCESS: Standard sale approved and processed successfully.")
    except Exception as e:
        log(f"❌ FAILURE: Valid sale was rejected. Error: {e}")
        import traceback
        log(traceback.format_exc())

    log("\n--- Simulation Complete ---")

if __name__ == "__main__":
    run()
