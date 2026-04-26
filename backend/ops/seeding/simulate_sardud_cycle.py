import os
import django
from decimal import Decimal
from datetime import date, timedelta
import json
import uuid

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from smart_agri.core.models.farm import Farm
from smart_agri.core.models.planning import CropPlan
from smart_agri.core.models.hr import Employee
from smart_agri.core.models import Location, Crop, CropProduct
from smart_agri.inventory.models import Item
from smart_agri.sales.models import Customer
from smart_agri.finance.models import FiscalPeriod

User = get_user_model()

def run_simulation():
    print("==================================================")
    print("     Sardud Farm End-to-End Simulation Start      ")
    print("==================================================")
    
    # 1. Setup Client and Auth
    client = APIClient()
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        print("FATAL: No superuser found. Create one first.")
        return
    client.force_authenticate(user=user)
    print(f"[+] Authenticated as {user.username}")

    # 2. Get Farm ID
    farm = Farm.objects.filter(name__contains="سردود").first()
    if not farm:
        print("FATAL: Sardud Farm not found!")
        return
    farm_id = farm.id
    print(f"[+] Farm Found: {farm.name} (ID: {farm_id})")

    # 3. Get Crop Plans (Seasonal & Perennial)
    plans = list(CropPlan.objects.filter(farm=farm))
    if len(plans) < 2:
        print(f"FATAL: Missing crop plans! Found only {len(plans)}. Ensure seed script ran properly.")
        return
    seasonal_plan = plans[0]
    perennial_plan = plans[1]
    print(f"[+] Seasonal Plan ID: {seasonal_plan.id}, Perennial Plan ID: {perennial_plan.id}")

    # 4. Get Employees
    emp_off = Employee.objects.filter(farm=farm, employee_id="SARD-OFF-01").first()
    emp_cas = Employee.objects.filter(farm=farm, employee_id="SARD-CAS-01").first()
    if not emp_off or not emp_cas:
        print("FATAL: Employees missing.")
        return
    
    # Step 1: Create a Daily Log
    print("\n[STEP 1] Creating Daily Log...")
    log_payload = {
        "farm": farm_id,
        "log_date": date.today().isoformat(),
        "notes": "محاكاة الإنجاز اليومي - سردود (موسمي ومعمر)"
    }
    res = client.post('/api/v1/daily-logs/', data=log_payload, format='json', HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4()))
    if res.status_code != 201:
        print(f"[-] ERROR Creating Daily Log (Code: {res.status_code}): {res.data}")
        return
    log_id = res.data['id']
    print(f"[+] Daily Log created successfully. ID: {log_id}")

    # Step 2: Add Activity for Seasonal Crop
    print("\n[STEP 2] Creating Seasonal Activity (Simple Data Flow)...")
    act_payload_seasonal = {
        "log": log_id,
        "crop_plan": seasonal_plan.id,
        "type": "PLANTING",
        "name": "زراعة القمح - مساحة 10 هكتار",
        "notes": "العمل بالعمال العرضية والرسمية",
        # Smart Cards Mapping - Simple Employees list
        "employees": [emp_off.id, emp_cas.id],
        "materials": [],
        "machines": []
    }
    res_act1 = client.post('/api/v1/activities/', data=act_payload_seasonal, format='json', HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4()))
    if res_act1.status_code != 201:
         print(f"[-] ERROR Creating Seasonal Activity (Code: {res_act1.status_code}): {res_act1.data}")
         return
    print(f"[+] Seasonal Activity created. ID: {res_act1.data['id']}")

    # Step 3: Add Activity for Perennial Crop
    print("\n[STEP 3] Creating Perennial Activity (Tree Maintenance)...")
    act_payload_perennial = {
        "log": log_id,
        "crop_plan": perennial_plan.id,
        "type": "CROP_MAINTENANCE",
        "name": "تقليم أشجار المانجو",
        "notes": "تقليم 500 شجرة باستخدام عمال رسميين",
        "employees": [emp_off.id],
        "materials": [],
        "machines": []
    }
    res_act2 = client.post('/api/v1/activities/', data=act_payload_perennial, format='json', HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4()))
    if res_act2.status_code != 201:
         print(f"[-] ERROR Creating Perennial Activity (Code: {res_act2.status_code}): {res_act2.data}")
         return
    print(f"[+] Perennial Activity created. ID: {res_act2.data['id']}")

    # Step 4: Submit the Daily Log
    print("\n[STEP 4] Submitting Daily Log...")
    res_sub = client.post(f'/api/v1/daily-logs/{log_id}/submit/', format='json', HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4()))
    if res_sub.status_code not in [200, 201]:
         print(f"[-] ERROR Submitting Daily Log (Code: {res_sub.status_code}): {res_sub.data}")
         return
    print(f"[+] Daily Log Submitted successfully.")

    # Step 5: Procurement & GRN
    print("\n[STEP 5] Procurement & GRN (Receiving Goods)...")
    urea = Item.objects.filter(name__contains='يوريا').first()
    store_loc = Location.objects.filter(farm=farm, name__contains='مستودع').first()
    
    if urea and store_loc:
        grn_payload = {
            "farm_id": farm.id,
            "item_id": urea.id,
            "location_id": store_loc.id,
            "qty": "500.00",
            "unit_cost": "850.00",
            "ref_id": "PO-2026-001"
        }
        res_grn = client.post('/api/v1/item-inventories/receive/', data=grn_payload, format='json', HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4()))
        if res_grn.status_code == 200:
            print(f"[+] GRN Processed for {urea.name}: Received 500 KG at 850 YER/unit.")
        else:
            print(f"[-] ERROR Processing GRN (Code: {res_grn.status_code}): {res_grn.data}")
            return

    # Step 6: Harvest
    print("\n[STEP 6] Harvest & Zakat calculation (Tomato Crop)...")
    tomato = Crop.objects.filter(name__contains='طماطم').first()
    if tomato:
        tomato_product = CropProduct.objects.filter(crop=tomato).first()
        if not tomato_product:
            print("[-] Creating missing CropProduct for Tomato")
            tomato_item, _ = Item.objects.get_or_create(name="طماطم حصاد", defaults={"group": "Goods"})
            tomato_product = CropProduct.objects.create(farm=farm, crop=tomato, name="طماطم تصدير فرز اول", is_primary=True, item=tomato_item)
            
        harvest_payload = {
            "farm": farm_id,
            "crop": tomato.id,
            "crop_plan": seasonal_plan.id,
            "product": tomato_product.id,
            "location": seasonal_plan.location.id,
            "harvest_date": (date.today() + timedelta(days=90)).isoformat(),
            "quantity": "25000.00",
            "grade": "First",
            "uom": "kg"
        }
        res_harv = client.post('/api/v1/harvest-logs/', data=harvest_payload, format='json', HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4()))
        if res_harv.status_code == 201:
            print(f"[+] Harvest Processed: 25,000 KG of {tomato.name}")
            
            # Explicitly receive harvested item to inventory
            if tomato_product.item and store_loc:
                grn_payload_harvest = {
                    "farm_id": farm.id,
                    "item_id": tomato_product.item.id,
                    "location_id": store_loc.id,
                    "qty": "25000.00",
                    "unit_cost": "200.00",
                    "ref_id": f"HARV-SIM-{res_harv.data.get('id', 'test')}"
                }
                client.post('/api/v1/item-inventories/receive/', data=grn_payload_harvest, format='json', HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4()))
                print(f"[+] Harvest auto-GRN completed for {tomato_product.item.name}.")
                
        else:
            print(f"[-] ERROR Processing Harvest (Code: {res_harv.status_code}): {res_harv.data}")
            return

    # Step 7: Financial/Sales
    print("\n[STEP 7] Financial/Sales: Sales Processing (Tomato Crop)...")
    customer, _ = Customer.objects.get_or_create(name='شركة التصدير الزراعية', defaults={'phone': '700000000'})
    sale_payload = {
        "customer": customer.id,
        "location": store_loc.id,
        "invoice_date": (date.today() + timedelta(days=95)).isoformat(),
        "notes": "بيع محصول طماطم سردود",
        "items": [
            {
                "item": tomato_product.item.id,
                "qty": "20000.00",
                "unit_price": "600.00"
            }
        ]
    }
    res_sale = client.post('/api/v1/sales-invoices/', data=sale_payload, format='json', HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4()))
    if res_sale.status_code == 201:
        sale_id = res_sale.data['id']
        print(f"[+] Sales Invoice Created. ID: {sale_id}")
        
        # Confirm Sale
        res_conf = client.post(f'/api/v1/sales-invoices/{sale_id}/confirm/', format='json', HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4()))
        if res_conf.status_code == 200:
            print(f"[+] Sales Invoice Confirmed! (Sector Settlement triggered)")
        else:
            print(f"[-] ERROR Confirming Sale (Code: {res_conf.status_code}): {res_conf.data}")
            return
    else:
        print(f"[-] ERROR Creating Sale (Code: {res_sale.status_code}): {res_sale.data}")
        return

    # Step 8: Fiscal Period Close
    print("\n[STEP 8] Hard Close of Fiscal Period...")
    period = FiscalPeriod.objects.filter(is_closed=False, fiscal_year__farm=farm).order_by('month').first()
    if period:
        res_soft = client.post(f'/api/v1/finance/fiscal-periods/{period.id}/soft-close/', format='json', HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4()))
        if res_soft.status_code == 200:
            print(f"[+] Fiscal Period {period.month} Soft Closed successfully.")
            res_hard = client.post(f'/api/v1/finance/fiscal-periods/{period.id}/hard-close/', format='json', HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4()))
            if res_hard.status_code == 200:
                print(f"[+] Fiscal Period {period.month} Hard Closed successfully.")
            else:
                print(f"[-] ERROR Hard Closing Fiscal Period (Code: {res_hard.status_code}): {res_hard.data}")
        else:
             print(f"[-] ERROR Soft Closing Fiscal Period (Code: {res_soft.status_code}): {res_soft.data}")
    else:
        print("[-] No open Fiscal Period found to close.")

    print("\n[√] SIMULATION CYCLE 1 COMPLETE: End-to-End Sardud Farm Operations.")

if __name__ == "__main__":
    run_simulation()
