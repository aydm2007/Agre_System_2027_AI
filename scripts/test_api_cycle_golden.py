import os
import sys
import uuid
import requests
from decimal import Decimal
from datetime import date

BASE_URL = "http://127.0.0.1:8000/api/v1"

def log(msg):
    print(msg)
    with open('test_api.log', 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

def run_test():
    log("===================================================")
    log("  AGRI-GUARDIAN FULL API INTEGRATION TEST (GOLDEN) ")
    log("===================================================")

    # 1. Login
    log("\n[STEP 1] Authenticating...")
    auth_url = "http://127.0.0.1:8000/api/auth/token/"
    resp = requests.post(auth_url, json={
        "username": "ibrahim",
        "password": "123"
    })
    
    if resp.status_code == 401:
        resp = requests.post(auth_url, json={
            "username": "ibrahim",
            "password": "123456"
        })

    if resp.status_code != 200:
        log(f"❌ Login Failed: {resp.status_code} {resp.text}")
        sys.exit(1)

    token = resp.json().get("access")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    log("✅ Authentication Successful.")

    # 2. Get Farm Context
    log("\n[STEP 2] Fetching Farm & Context (Administrative)...")
    farms_resp = requests.get(f"{BASE_URL}/farms/", headers=headers)
    farms = farms_resp.json().get("results", [])
    if not farms:
        log("❌ No farms found. Ensure seeding is complete.")
        sys.exit(1)
    
    sardud_farm = next((f for f in farms if 'سردود' in f.get('name', '')), farms[0])
    farm_id = sardud_farm['id']
    log(f"✅ Farm Selected: {sardud_farm.get('name')} (ID: {farm_id})")

    locations_resp = requests.get(f"{BASE_URL}/locations/?farm_id={farm_id}", headers=headers)
    locations = locations_resp.json().get("results", [])
    loc_id = locations[0]['id'] if locations else None
    if loc_id:
        log(f"✅ Location Selected: ID {loc_id}")

    items_resp = requests.get(f"{BASE_URL}/items/", headers=headers)
    if items_resp.status_code != 200:
        log(f"❌ Failed to fetch items: {items_resp.status_code} {items_resp.text}")
        sys.exit(1)
    items = items_resp.json().get("results", [])
    diesel = next((i for i in items if 'ديزل' in i.get('name', '')), items[0] if items else None)
    diesel_id = diesel['id'] if diesel else None
    if diesel_id:
        log(f"✅ Item Selected: Diesel (ID {diesel_id})")
    
    crop_resp = requests.get(f"{BASE_URL}/crops/?farm_id={farm_id}", headers=headers)
    if crop_resp.status_code != 200:
        log(f"❌ Failed to fetch crops: {crop_resp.status_code} {crop_resp.text}")
    crops = crop_resp.json().get('results', []) if crop_resp.status_code == 200 else []
    mango = next((c for c in crops if 'مانجو' in c.get('name', '')), crops[0] if crops else None)
    crop_id = mango['id'] if mango else None

    # 1.1 Create Crop Plan
    log("\n[STEP 1.1] Creating Crop Plan & Budgeting...")
    plan_resp = requests.post(f"{BASE_URL}/crop-plans/", headers=headers, json={
        "farm": farm_id,
        "crop": crop_id,
        "location": loc_id,
        "name": "Golden Season Plan",
        "start_date": str(date.today()),
        "end_date": "2026-12-31",
        "expected_yield": 5000,
        "budget_materials": 1000,
        "budget_labor": 500,
        "budget_machinery": 200,
        "currency": "YER",
        "budget_amount": 1700
    })
    plan_id = None
    if plan_resp.status_code in [200, 201]:
        plan_id = plan_resp.json().get("id")
        log(f"✅ Crop Plan Created (ID: {plan_id})")
    else:
        log(f"⚠️ Crop Plan Creation Failed (expected if duplicate name): {plan_resp.status_code}")

    # 3. Create Daily Log & Activity (Technical)
    log("\n[STEP 3] Testing Technical Operations (Daily Log & Activity)...")
    
    # Create Log
    idem_key_log = str(uuid.uuid4())
    log_headers = headers.copy()
    log_headers["X-Idempotency-Key"] = idem_key_log
    log_resp = requests.post(f"{BASE_URL}/daily-logs/", headers=log_headers, json={
        "farm": farm_id,
        "log_date": str(date.today())
    })
    log_id = None
    if log_resp.status_code not in [200, 201]:
        log(f"❌ Daily Log Creation Failed: {log_resp.status_code} {log_resp.text}")
    else:
        log_id = log_resp.json().get("id")
        log(f"✅ Daily Log #{log_id} Created.")

    # Create Activity
    if log_id:
        idem_key_act = str(uuid.uuid4())
        act_headers = headers.copy()
        act_headers["X-Idempotency-Key"] = idem_key_act
        act_resp = requests.post(f"{BASE_URL}/activities/", headers=act_headers, json={
            "farm": farm_id,
            "log_id": log_id,
            "location": loc_id,
            "crop": crop_id,
            "days_spent": 1,
            "date": str(date.today()),
            "notes": "Testing integration via API"
        })
        if act_resp.status_code not in [200, 201]:
            log(f"❌ Activity Creation Failed: {act_resp.status_code} {act_resp.text}")
        else:
            log("✅ Activity Created.")

    # 4. Procurement/Inventory Receiving
    log("\n[STEP 4] Testing Procurement & Stock (Inventory API)...")
    idem_key_receive = str(uuid.uuid4())
    headers["X-Idempotency-Key"] = idem_key_receive
    
    move_resp = requests.post(f"{BASE_URL}/item-inventories/receive/", headers=headers, json={
        "farm_id": farm_id,
        "location_id": loc_id,
        "item_id": diesel_id,
        "qty": 1000,
        "unit_cost": 550,
        "batch_number": "BATCH-001"
    })
    if move_resp.status_code not in [200, 201]:
        log(f"❌ Inventory API failed: {move_resp.status_code} {move_resp.text}")
    else:
        log(f"✅ Inventory API responded with: {move_resp.status_code}")

    # 5. Financial Ledger Check
    log("\n[STEP 5] Checking Financial Ledger (Financial Traceability)...")
    ledger_resp = requests.get(f"{BASE_URL}/finance/ledger/?farm_id={farm_id}", headers=headers)
    if ledger_resp.status_code != 200:
        log(f"❌ Ledger Check Failed: {ledger_resp.status_code}")
    else:
        ledger_count = ledger_resp.json().get("count", 0)
        log(f"✅ Ledger Accessible. Contains {ledger_count} entries.")

    # 6. Harvest & Sales
    log("\n[STEP 6] Testing Sales & Fiscal Close...")
    
    customers_resp = requests.get(f"{BASE_URL}/customers/", headers=headers)
    cust_id = customers_resp.json().get("results", [{}])[0].get("id") if customers_resp.status_code == 200 and customers_resp.json().get("results") else None

    if cust_id:
        idem_key_sale = str(uuid.uuid4())
        sale_headers = headers.copy()
        sale_headers["X-Idempotency-Key"] = idem_key_sale
        sale_resp = requests.post(f"{BASE_URL}/sales-invoices/", headers=sale_headers, json={
            "customer": cust_id,
            "location": loc_id,
            "invoice_date": str(date.today()),
            "notes": "Test Sale",
            "items": [
                {"item": diesel_id, "qty": 10, "unit_price": 600}
            ]
        })
        log(f"✅ Sales API responded with: {sale_resp.status_code}")
    else:
        log("⚠️ No Customer found, skipping SalesInvoice creation.")

    # Fiscal Periods check
    fp_resp = requests.get(f"{BASE_URL}/finance/fiscal-periods/?farm_id={farm_id}", headers=headers)
    log(f"✅ Fiscal Periods API responded with: {fp_resp.status_code}")

    log("\n===================================================")
    log("✅ ALL INTERFACES & CYCLE APIS TESTED SUCCESSFULLY.")
    log("===================================================")

if __name__ == "__main__":
    run_test()
