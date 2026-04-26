import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from smart_agri.core.models import CropPlan, Farm, Item, Unit, Location, LocationCrop, HarvestLog, HarvestLot
from smart_agri.sales.models import SalesInvoice, SalesInvoiceItem, Customer
from django.contrib.auth import get_user_model

def run_simulation():
    with open('step3_output.txt', 'w', encoding='utf-8') as f:
        f.write("Starting Step 3 Simulation (API Based)...\n")
        
        plan = CropPlan.objects.filter(name__icontains='خطة التدقيق النهائية 2026').last()
        if not plan:
            f.write("Crop Plan not found.\n")
            return
            
        farm = plan.farm
        
        # 1. Harvest Simulation
        f.write("\n--- 1. Simulating Harvest ---\n")
        loc_crop = LocationCrop.objects.filter(farm=farm, crop=plan.crop).first()
        if not loc_crop:
            f.write("No LocationCrop found for this farm and crop. Let's create one.\n")
            loc = Location.objects.filter(farm=farm).first()
            if not loc:
                f.write("Failed to find any location.\n")
                return
            loc_crop = LocationCrop.objects.create(farm=farm, location=loc, crop=plan.crop, area=10)

        # Creating Harvest Log directly mimicking the business logic payload
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
            
            lot, curr = HarvestLot.objects.get_or_create(
                farm=farm,
                harvest_log=harvest_log,
                crop=plan.crop,
                lot_number="LOT-E2E-2026",
                defaults={
                    'qty_initial': Decimal('1000.00'),
                    'qty_available': Decimal('1000.00'),
                    'unit_cost': Decimal('50.00')
                }
            )
            f.write(f"Success: Harvest Lot {lot.lot_number} created/found. Cost/Unit: {lot.unit_cost}\n")
        except Exception as e:
            f.write(f"Error during Harvest: {e}\n")
            return

        # 2. Sales Simulation & Pricing Engine 
        f.write("\n--- 2. Simulating Sales & Governance Engine ---\n")
        
        customer, _ = Customer.objects.get_or_create(name="عميل اختبار", defaults={'phone': '0500000000'})
        
        invoice = SalesInvoice.objects.create(
            farm=farm,
            customer=customer,
            date='2026-06-05',
            status='draft',
            notes='E2E Audit Sales'
        )
        
        f.write("Attempting to sell below cost to trigger Governance Auto-Pricing Engine...\n")
        try:
            # Sell at 10.00 when cost is 50.00 - should trigger the Auto-Pricing engine
            item = SalesInvoiceItem(
                invoice=invoice,
                harvest_lot=lot,
                qty=Decimal('100.00'),
                unit_price=Decimal('10.00') # Below cost!
            )
            item.clean()
            item.save()
            f.write("FAILURE: System allowed selling below cost!\n")
        except Exception as e:
            f.write(f"SUCCESS: System blocked the sale as expected. Governance Validation Error: {e}\n")
            
        f.write("Attempting to sell at a profitable price...\n")
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
            f.write("SUCCESS: System allowed the profitable sale.\n")
            
            # Approve invoice
            invoice.status = 'approved'
            invoice.clean()
            invoice.save()
            f.write("Invoice Approved and Processed.\n")
        except Exception as e:
            f.write(f"FAILURE: Profitable sale failed unexpectedly. Error: {e}\n")

if __name__ == '__main__':
    run_simulation()
