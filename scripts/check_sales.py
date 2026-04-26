
import os
import django
from django.db import connection

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from smart_agri.sales.models import Sale, Customer

def check_sales_data():
    print("\n--- Checking Sales Data ---")
    customer_count = Customer.objects.count()
    sale_count = Sale.objects.count()
    
    print(f"Customers: {customer_count}")
    print(f"Sales: {sale_count}")

    if sale_count > 0:
        total_revenue = 0
        for sale in Sale.objects.all():
            total_revenue += sale.total_amount
        print(f"Total Revenue in DB: {total_revenue}")
    else:
        print("No sales found. Dashboard revenue will be 0.")

if __name__ == '__main__':
    check_sales_data()
