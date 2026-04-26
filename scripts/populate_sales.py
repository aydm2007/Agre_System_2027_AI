
import os
import django
from decimal import Decimal
from django.utils import timezone

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from smart_agri.sales.models import Sale, Customer, SaleItem
from smart_agri.core.models import CropPlan, Location, Item

def populate_sales():
    print("\n--- Populating Sales Data ---")
    
    if Sale.objects.count() > 0:
        print("Sales data already exists. Skipping population.")
        return

    # Ensure dependencies exist
    customer, _ = Customer.objects.get_or_create(
        name="سوق الجملة المركزي",
        defaults={'phone': '0555555555', 'customer_type': 'wholesale'}
    )

    plan = CropPlan.objects.filter(deleted_at__isnull=True).first()
    if not plan:
        print("No active CropPlan found. Cannot create sale.")
        return

    location = Location.objects.first()
    item = Item.objects.first()

    # Create Sale
    sale = Sale.objects.create(
        crop_plan=plan,
        customer=customer,
        location=location,
        sale_date=timezone.now().date(),
        status='paid',
        total_amount=0, # Will update
        notes="بيع تجريبي"
    )

    # Create Item
    qty = Decimal('100.0')
    price = Decimal('50.0')
    SaleItem.objects.create(
        sale=sale,
        item=item,
        product_name=item.name if item else "Unknown Product",
        quantity=qty,
        unit_price=price,
        total_price=qty * price
    )

    # Update total
    sale.total_amount = qty * price
    sale.save()
    
    print(f"Created Sale: {sale} with Total: {sale.total_amount}")

if __name__ == '__main__':
    populate_sales()
