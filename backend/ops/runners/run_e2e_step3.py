import os
import sys

print("Initializing Step 3 E2E Django Environment...")

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
import django
django.setup()

from smart_agri.core.models import CropPlan, Location, DailyLog, Activity, ActivityHarvest, HarvestLot
from smart_agri.inventory.models import Item, ItemInventory, Unit
from smart_agri.sales.models import SalesInvoice, SalesInvoiceItem, Customer
from smart_agri.sales.services import SaleService
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils import timezone

def run():
    print("\n--- [Audit Step 3: Harvest and Sales Simulation] ---")
    
    plan = CropPlan.objects.filter(name__icontains='خطة التدقيق النهائية 2026').last()
    if not plan:
        print("❌ Crop Plan 'خطة التدقيق النهائية 2026' not found.")
        return
        
    farm = plan.farm
    print(f"✅ Found Crop Plan for Farm: {farm.name}")
    
    today = timezone.now().date()
    
    # [Phase A] Harvest Operations
    print("\n[Phase A] Simulating Harvest Operation...")
    loc = Location.objects.filter(farm=farm).first()
    if not loc:
         print("❌ Failed to find any location for farm.")
         return

    try:
        daily_log = DailyLog.objects.create(farm=farm, log_date=today, status='APPROVED')
        activity = Activity.objects.create(
            log=daily_log, crop_plan=plan, crop=plan.crop, location=loc, data={"note": "E2E Harvest"}
        )
        
        lot, _ = HarvestLot.objects.get_or_create(
            farm=farm, crop=plan.crop, crop_plan=plan, location=loc, harvest_date=today,
            defaults={'quantity': Decimal('1000.00'), 'uom': 'kg', 'grade': 'First'}
        )

        harvest_activity = ActivityHarvest.objects.create(
            activity=activity, harvest_quantity=Decimal('1000.00'), uom='kg', lot=lot
        )
        print("✅ DailyLog, Activity, ActivityHarvest, and HarvestLot generated successfully.")
    except Exception as e:
        print(f"❌ Error during Harvest Creation: {e}")
        return

    # Create missing Inventory linkages for Sales Governance testing
    user_admin = User.objects.filter(is_superuser=True).first()
    if not user_admin:
        user_admin = User.objects.create_superuser('admin_audit', 'a@a.com', 'admin')

    unit, _ = Unit.objects.get_or_create(name_ar="كيلو", defaults={"name_en": "KG"})
    base_cost = Decimal('50.00')
    item, _ = Item.objects.get_or_create(
        name="محصول مانجو السردود (تجربة)", 
        defaults={"type": "product", "uom": "kg", "unit": unit, "unit_price": base_cost}
    )
    # Give it inventory so validation passes
    inv, _ = ItemInventory.objects.get_or_create(
        farm=farm, location=loc, item=item, defaults={'qty': Decimal('1000.00')}
    )

    # [Phase B] Sales Governance
    print("\n[Phase B] Simulating Sales Governance & Pricing Engine...")
    customer, _ = Customer.objects.get_or_create(name="عميل اختبار", phone="0500000000")
    
    invoice = SalesInvoice.objects.create(
        farm=farm, location=loc, customer=customer, invoice_date=today, status='draft', notes='E2E Audit Sales', created_by=user_admin
    )
    
    print("\n1. Testing Rule: Preventing sales below cost (Cost=50.00, Attempted Price=10.00)")
    item_sale = SalesInvoiceItem.objects.create(
        invoice=invoice, item=item, harvest_lot=lot, qty=Decimal('100.00'), unit_price=Decimal('10.00'), total=Decimal('1000.00')
    )
    
    try:
        SaleService.check_confirmability(invoice, user=user_admin)
        print("❌ FAILURE: System bypass! Allowed sale below cost without error.")
    except Exception as e:
        print(f"✅ SUCCESS: System intercepted the under-cost sale! Validation Error: {e}")

    print("\n2. Testing Rule: Allowing profitable sale (Cost=50.00, Attempted Price=75.00)")
    item_sale.unit_price = Decimal('75.00')
    item_sale.total = Decimal('7500.00')
    item_sale.save()
    
    invoice.total_amount = Decimal('7500.00')
    invoice.net_amount = Decimal('7500.00')
    invoice.save()

    try:
        SaleService.confirm_sale(invoice, user=user_admin)
        print("✅ SUCCESS: Standard sale approved and inventory/ledgers updated successfully.")
    except Exception as e:
        print(f"❌ FAILURE: Valid sale was rejected. Error: {e}")

    print("\n--- Simulation Complete ---")

if __name__ == "__main__":
    run()
