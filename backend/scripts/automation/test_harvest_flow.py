import os
import sys
import django
import json
from decimal import Decimal

# Setup Django Environment
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from smart_agri.core.models import Farm, Crop, Item, Unit, CropProduct
from smart_agri.accounts.models import FarmMembership

User = get_user_model()

# ANSI Colors
GREEN = '\033[92m'
RED = '\033[91m'
RESET = '\033[0m'
BOLD = '\033[1m'

def log(message, status="INFO"):
    if status == "PASS":
        print(f"[{GREEN}PASS{RESET}] {message}")
    elif status == "FAIL":
        print(f"[{RED}FAIL{RESET}] {message}")
    else:
        print(f"[{BOLD}INFO{RESET}] {message}")

def run_tests():
    print(f"\n{BOLD}=== Agri-Guardian: Harvest Products Automation Test ==={RESET}\n")

    # 1. Setup Test Data
    log("Setting up Test Data...")
    user_a, _ = User.objects.get_or_create(username='test_user_a', defaults={'email': 'a@test.com'})
    user_b, _ = User.objects.get_or_create(username='test_user_b', defaults={'email': 'b@test.com'})
    
    farm_a, _ = Farm.objects.get_or_create(name='Test Farm A', defaults={'area': 100})
    farm_b, _ = Farm.objects.get_or_create(name='Test Farm B', defaults={'area': 50})
    
    # Assign Memberships
    FarmMembership.objects.get_or_create(user=user_a, farm=farm_a, role='manager')
    FarmMembership.objects.get_or_create(user=user_b, farm=farm_b, role='manager')
    
    crop, _ = Crop.objects.get_or_create(name='Test Wheat', defaults={'mode': 'Open'})
    item, _ = Item.objects.get_or_create(name='Wheat Grain', defaults={'group': 'Produce', 'uom': 'kg'})
    unit, _ = Unit.objects.get_or_create(name='Sack', code='SCK', defaults={'conversion_factor': 50})

    client = Client()
    client.force_login(user_a)

    # 2. Execute Tests
    
    # --- Test Case BE-01: Strict Farm Enforcement ---
    log("Running BE-01: Strict Farm Enforcement (Expect 400)...")
    payload_invalid = {
        "farm": None, # Violation of Axis 6
        "crop": crop.id,
        "item": item.id,
        "is_primary": False
    }
    res_invalid = client.post('/api/v1/crop-products/', data=json.dumps(payload_invalid), content_type='application/json')
    
    if res_invalid.status_code == 400 and 'farm' in res_invalid.json():
        log("BE-01 Passed: Null farm was rejected.", "PASS")
    else:
        log(f"BE-01 Failed: Expected 400, got {res_invalid.status_code}. Body: {res_invalid.json()}", "FAIL")

    # --- Test Case BE-02: Valid Creation ---
    log("Running BE-02: Valid Creation (Expect 201)...")
    payload_valid = {
        "farm": farm_a.id,
        "crop": crop.id,
        "item": item.id,
        "is_primary": True,
        "notes": "Automated Test",
        "units": [
            {"unit": unit.id, "multiplier": 1, "is_default": True}
        ]
    }
    res_valid = client.post('/api/v1/crop-products/', data=json.dumps(payload_valid), content_type='application/json')
    
    product_id = None
    if res_valid.status_code == 201:
        product_id = res_valid.json().get('id')
        log(f"BE-02 Passed: Product created with ID {product_id}.", "PASS")
    else:
        log(f"BE-02 Failed: Expected 201, got {res_valid.status_code}. Body: {res_valid.json()}", "FAIL")

    # --- Test Case BE-03: Data Integrity ---
    log("Running BE-03: Data Integrity Check...")
    if product_id:
        db_product = CropProduct.objects.get(id=product_id)
        if db_product.farm == farm_a and db_product.item == item:
             log("BE-03 Passed: DB Row matches payload.", "PASS")
        else:
             log(f"BE-03 Failed: DB Mismatch. Farm: {db_product.farm}, Item: {db_product.item}", "FAIL")
    else:
        log("BE-03 Skipped (BE-02 Failed)", "FAIL")

    # --- Test Case BE-04: Tenant Isolation (RLS) ---
    log("Running BE-04: Tenant Isolation / RLS...")
    client_b = Client()
    client_b.force_login(user_b) # Login as User B (Farm B)
    
    # Try to access User A's product
    res_rls = client_b.get(f'/api/v1/crop-products/{product_id}/') # Detail view if exists, or list
    res_list_b = client_b.get(f'/api/v1/harvest-product-catalog/?farm_id={farm_a.id}')
    
    # Expect 404/403 or Empty List depending on exact impl. 
    # Since Farm A is not User B's farm, he should not see it in catalog if filtered strictly.
    # Note: Catalog view often allows reading reference data if open, but Axis 6 implies strictness.
    # Let's check if the serializer allows reading another farm's data without explicit permission.
    
    # Actually, RLS policy for `core_cropproduct` is what matters. 
    # If RLS is active, `CropProduct.objects.all()` for User B should NOT return User A's product.
    
    # Let's count visible products
    visible_count = CropProduct.objects.filter(farm=farm_a).count() # This is superuser/system view
    # We need to simulate request user context for RLS, but Django Test Client + RLS middleware is complex.
    # Instead, we check the API response content.
    
    if res_list_b.status_code == 200:
        data_b = res_list_b.json()
        # If data is empty or filtered, PASS.
        # But wait, User B *might* have read access to Farm A if allowed? No, strict isolation.
        log(f"BE-04 Check: User B sees {len(data_b)} items from Farm A.", "INFO")
        # In strict mode, this should be 0.
        if len(data_b) == 0:
            log("BE-04 Passed: Cross-farm read blocked/empty.", "PASS")
        else:
             log("BE-04 Warning: Cross-farm read passed. Verify if this is intended (Global Catalog vs Private).", "FAIL")

    # --- Test Case BE-05: Idempotency ---
    log("Testing BE-05: Cleanup...")
    # Clean up
    if product_id:
        CropProduct.objects.filter(id=product_id).delete()
    log("Cleanup Complete.", "INFO")

if __name__ == '__main__':
    run_tests()
