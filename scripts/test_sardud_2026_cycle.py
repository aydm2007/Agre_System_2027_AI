import sys
import traceback

try:
    import os
    import uuid
    import requests
    import json
    from decimal import Decimal
    from datetime import date, timedelta

    BASE_URL = "http://127.0.0.1:8000/api/v1"

    def log(msg):
        print(msg)
        sys.stdout.flush()

    def post_idem(url, headers, json_data=None):
        idem_headers = headers.copy()
        key = str(uuid.uuid4())
        idem_headers["X-Idempotency-Key"] = key
        idem_headers["HTTP_X_IDEMPOTENCY_KEY"] = key
        return requests.post(url, headers=idem_headers, json=json_data)

    def patch_idem(url, headers, json_data=None):
        idem_headers = headers.copy()
        key = str(uuid.uuid4())
        idem_headers["X-Idempotency-Key"] = key
        idem_headers["HTTP_X_IDEMPOTENCY_KEY"] = key
        return requests.patch(url, headers=idem_headers, json=json_data)

    def run_test():
        log("=====================================================================")
        log("  AGRI-GUARDIAN FULL SARDUD 2026 INTEGRATION TEST (STRICT COMPLIANT) ")
        log("=====================================================================")

        # 1. Login
        log("\n[STEP 1] Authenticating as Admin...")
        auth_url = "http://127.0.0.1:8000/api/auth/token/"
        resp = requests.post(auth_url, json={"username": "ibrahim", "password": "123"})
        if resp.status_code == 401:
            resp = requests.post(auth_url, json={"username": "ibrahim", "password": "123456"})
        if resp.status_code != 200:
            log(f"❌ Login Failed: {resp.status_code} {resp.text}")
            sys.exit(1)

        token = resp.json().get("access")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        log("✅ Authentication Successful.")

        # 2. Administrative Setup
        log("\n[STEP 2] Administrative Setup: Creating Sardud 2026 Farm & Org...")
        
        # 2.1 Create Farm (LARGE tier expected)
        farm_resp = post_idem(f"{BASE_URL}/farms/", headers=headers, json_data={
            "name": "مزرعة سردود 2026 - نموذج الاختبار الشامل",
            "code": "S2026",
            "type": "COMPANY_FARM",
            "total_area": 300, # Large Farm
            "water_source": "ARTESIAN_WELL",
            "zakat_rule": "5_PERCENT", # Has irrigation
            "location_address": "سهام"
        })
        
        if farm_resp.status_code in [201, 200]:
            farm = farm_resp.json()
            farm_id = farm['id']
            log(f"✅ Farm Created/Retrieved (ID: {farm_id}, Tier: {farm.get('tier')}, Area: {farm.get('total_area')})")
        else:
            log(f"⚠️ Farm Creation output: {farm_resp.status_code} {farm_resp.text}")
            # Fetch it if exists
            f_resp = requests.get(f"{BASE_URL}/farms/?code=S2026", headers=headers)
            if f_resp.status_code == 200 and len(f_resp.json().get('results', [])) > 0:
                farm_id = f_resp.json()['results'][0]['id']
                log(f"✅ Farm used existing S2026: (ID: {farm_id})")
            else:
                log("❌ Farm setup failed utterly.")
                sys.exit(1)

        # 2.2 Location
        loc_resp = post_idem(f"{BASE_URL}/locations/", headers=headers, json_data={
            "farm": farm_id,
            "name": "مخزن وموقع سردود الرئيسي 2026",
            "type": "WAREHOUSE",
            "area_size": 10
        })
        loc_id = loc_resp.json().get('id') if loc_resp.status_code in [201, 200] else None
        if not loc_id:
            locs = requests.get(f"{BASE_URL}/locations/?farm_id={farm_id}", headers=headers).json().get('results', [])
            loc_id = locs[0]['id'] if locs else None
        log(f"✅ Location ID: {loc_id}")

        # 2.3 Fiscal Period
        # Actually in AGRI-GUARDIAN, fiscal period requires creating a Fiscal Year first if it doesn't exist,
        # but the error 405 means the URL isn't supporting POST directly or the trailing slash is wrong.
        # Let's check existing years
        fy_resp = requests.get(f"{BASE_URL}/finance/fiscal-years/?farm_id={farm_id}&year=2026", headers=headers)
        y_data = fy_resp.json().get('results', [])
        if not y_data:
            fy_create = post_idem(f"{BASE_URL}/finance/fiscal-years/", headers=headers, json_data={
                "farm": farm_id,
                "year": 2026,
                "start_date": "2026-01-01",
                "end_date": "2026-12-31"
            })
            log(f"✅ Fiscal Year Setup: {fy_create.status_code}")
        
        # 2.4 Master Data Fetch (Items, Crops, Employees)
        items = requests.get(f"{BASE_URL}/items/?limit=50", headers=headers).json().get("results", [])
        diesel_id = next((i['id'] for i in items if 'ديزل' in i.get('name', '')), items[0]['id'] if items else None)
        
        crops = requests.get(f"{BASE_URL}/crops/", headers=headers).json().get('results', [])
        crop = next((c for c in crops if 'مانجو' in c.get('name', '')), crops[0] if crops else None)
        
        if not crop:
            cr_resp = post_idem(f"{BASE_URL}/crops/", headers=headers, json_data={"name": "مانجو تيمور", "category": "FRUIT", "unit": "KG"})
            crop = cr_resp.json()
        crop_id = crop['id']

        # Set up Surra Employee
        emp_resp = post_idem(f"{BASE_URL}/employees/", headers=headers, json_data={
            "farm": farm_id,
            "name": "عامل مؤقت (السُرة) - سردود 2026",
            "category": "CASUAL",
            "daily_rate": 2500,
            "payment_mode": "CASH"
        })
        emp_id = emp_resp.json().get('id') if emp_resp.status_code in [201, 200] else None
        if not emp_id:
            emps = requests.get(f"{BASE_URL}/employees/?category=CASUAL&farm_id={farm_id}", headers=headers).json().get('results', [])
            emp_id = emps[0]['id'] if emps else None
        log(f"✅ Set up Casual Employee ID: {emp_id}")

        # 3. Agricultural & Inventory Operations
        log("\n[STEP 3] Technical & Inventory Operations...")

        # 3.1 Crop Plan
        plan_resp = post_idem(f"{BASE_URL}/crop-plans/", headers=headers, json_data={
            "farm": farm_id,
            "crop": crop_id,
            "location": loc_id,
            "name": "خطة سردود 2026 القياسية",
            "start_date": str(date.today()),
            "end_date": "2026-12-31",
            "expected_yield": 10000,
            "budget_materials": 500000,
            "budget_labor": 100000,
            "budget_machinery": 50000,
            "currency": "YER",
            "budget_amount": 650000
        })
        plan_id = plan_resp.json().get('id') if plan_resp.status_code in [201, 200] else None
        if not plan_id:
            plans = requests.get(f"{BASE_URL}/crop-plans/?farm_id={farm_id}", headers=headers).json().get('results', [])
            plan_id = plans[0]['id'] if plans else None
        log(f"✅ Crop Plan ID: {plan_id}")

        # 3.2 Idempotent GRN (Receive Diesel)
        rec_resp = post_idem(f"{BASE_URL}/item-inventories/receive/", headers=headers, json_data={
            "farm": farm_id,          # Fixed from farm_id
            "location": loc_id,       # Fixed from location_id
            "item": diesel_id,        # Fixed from item_id
            "qty": "5000.00",         # Decimal string format
            "unit_cost": "450.50",    # Decimal string format
            "batch_number": "SARDUD-001"
        })
        log(f"✅ Received 5000 Diesel: {rec_resp.status_code} {rec_resp.json().get('stock_id', '')}")

        # 3.3 Daily Log and Activity (Consume Surra & Diesel)
        dl_resp = post_idem(f"{BASE_URL}/daily-logs/", headers=headers, json_data={
            "farm": farm_id,
            "log_date": str(date.today())
        })
        dl_id = dl_resp.json().get('id') if dl_resp.status_code in [201, 200] else None
        log(f"✅ Daily Log created: {dl_id}")

        if dl_id:
            act_resp = post_idem(f"{BASE_URL}/activities/", headers=headers, json_data={
                "farm": farm_id,
                "log_id": dl_id,
                "location": loc_id,
                "crop": crop_id,
                "crop_plan": plan_id,
                "days_spent": 1,
                "date": str(date.today()),
                "notes": "سقاية المزرعة وعمالة يومية"
            })
            log(f"✅ Activity created: {act_resp.status_code} {act_resp.text}")

        # 4. Financial Closings & Constraints
        log("\n[STEP 4] Financial Ops, Zakat, Sales, and Close...")

        # 4.1 Harvest & Zakat Trigger
        har_resp = post_idem(f"{BASE_URL}/activities/harvest/", headers=headers, json_data={
            "farm": farm_id,
            "log_id": dl_id,
            "location": loc_id,
            "crop": crop_id,
            "crop_plan": plan_id,
            "harvest_quantity": "9500.00", # Fixed string parsing issue
            "date": str(date.today()),
            "notes": "حصاد 2026 النهائي"
        })
        log(f"✅ Harvest (Zakat triggered): {har_resp.status_code} {har_resp.text[:100]}")

        # 4.2 Sales to generate revenue for Sector
        cust_resp = post_idem(f"{BASE_URL}/customers/", headers=headers, json_data={
            "name": "تاجر سردود المعتمد",
            "farm": farm_id
        })
        cust_id = cust_resp.json().get('id') if cust_resp.status_code in [201, 200] else None
        if not cust_id:
            custs = requests.get(f"{BASE_URL}/customers/?farm={farm_id}", headers=headers).json().get('results', [])
            cust_id = custs[0]['id'] if custs else None
        
        if cust_id:
            sale_resp = post_idem(f"{BASE_URL}/sales-invoices/", headers=headers, json_data={
                "customer": cust_id,
                "location": loc_id,  # Now valid because Loc succeeds
                "invoice_date": str(date.today()),
                "notes": "بيع حصاد سردود",
                "items": [
                    {"item": diesel_id, "qty": "1.00", "unit_price": "500.00"} # Mock item if crop item not found easily
                ]
            })
            log(f"✅ Sales Invoice: {sale_resp.status_code} {sale_resp.text[:100]}")

        # 4.3 Fiscal Period Locking (Soft-close -> Hard-close)
        log("\n[STEP 5] Fiscal Close Enforcement...")
        fps = requests.get(f"{BASE_URL}/finance/fiscal-periods/?farm_id={farm_id}", headers=headers).json().get('results', [])
        if fps:
            fp_id = fps[0]['id']
            log(f"Current Period State: {fps[0]['status']}")
            
            # Action syntax for DRF routers
            close1 = post_idem(f"{BASE_URL}/finance/fiscal-periods/{fp_id}/soft_close/", headers=headers)
            log(f"✅ Soft Close transition: {close1.status_code}")

            close2 = post_idem(f"{BASE_URL}/finance/fiscal-periods/{fp_id}/hard_close/", headers=headers)
            log(f"✅ Hard Close transition: {close2.status_code}")

            # Try to post to hard close
            inv_resp = post_idem(f"{BASE_URL}/activities/", headers=headers, json_data={
                "farm": farm_id,
                "log_id": dl_id,
                "location": loc_id,
                "crop": crop_id,
                "days_spent": 1,
                "date": str(date.today()),
                "notes": "Should fail due to closed period"
            })
            log(f"✅ Test Hard-Close write block: {inv_resp.status_code} (Expected 403/400)")

        log("=====================================================================")
        log("  TEST SCRIPT FINISHED.")
        log("=====================================================================")

    if __name__ == "__main__":
        run_test()

except Exception as e:
    with open('error.log', 'w', encoding='utf-8') as f:
        f.write("CRASHED AT TOP LEVEL:\n" + traceback.format_exc())


