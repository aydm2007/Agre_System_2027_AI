import os
import sys
from decimal import Decimal
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")

import django
django.setup()

from smart_agri.core.services.asset_service import AssetService
from smart_agri.finance.models import FinancialLedger

def get_base_mock_asset():
    asset = MagicMock()
    asset.category = "Solar"
    asset.purchase_value = Decimal('100000.0000')
    asset.salvage_value = Decimal('10000.0000')
    asset.useful_life_years = 10
    asset.accumulated_depreciation = Decimal('0.0000')
    asset.pk = 999
    asset.name = "Test Solar Panel"
    asset.currency = "YER"
    asset.farm = MagicMock()
    asset.cost_center = MagicMock()
    return asset

def run():
    errors = 0
    print("[AGRI-GUARDIAN] Axis 9: Sovereign Liabilities & Solar Compliance Verification")
    tests_passed = 0

    # Test 1: calculate returns correct positive amount
    asset = get_base_mock_asset()
    # base = 90000, life_hours = 10*365*24 = 87600
    # hourly = 90000 / 87600 = 1.027397
    # hours = 24 -> 24 * 1.027397 = 24.6575
    res1 = AssetService.calculate_operational_solar_depreciation(asset, Decimal('24'))
    if res1 == Decimal('24.6575'): tests_passed += 1; print(" [OK] Test 1: Normal positive calculation returns correctly")
    else: errors += 1; print(f" [FAIL] Test 1: Expected 24.6575, got {res1}")

    # Test 2: zero hours
    res2 = AssetService.calculate_operational_solar_depreciation(asset, Decimal('0'))
    if res2 == Decimal('0.0000'): tests_passed += 1; print(" [OK] Test 2: Zero hours returns 0.0000")
    else: errors += 1; print(f" [FAIL] Test 2: {res2}")

    # Test 3: non-solar
    asset3 = get_base_mock_asset()
    asset3.category = "Machinery"
    res3 = AssetService.calculate_operational_solar_depreciation(asset3, Decimal('24'))
    if res3 == Decimal('0.0000'): tests_passed += 1; print(" [OK] Test 3: Non-solar returns 0.0000")
    else: errors += 1; print(f" [FAIL] Test 3")

    # Test 4: zero useful life
    asset4 = get_base_mock_asset()
    asset4.useful_life_years = 0
    res4 = AssetService.calculate_operational_solar_depreciation(asset4, Decimal('24'))
    if res4 == Decimal('0.0000'): tests_passed += 1; print(" [OK] Test 4: Zero useful life returns 0.0000")
    else: errors += 1; print(f" [FAIL] Test 4")

    # Test 5: negative value
    asset5 = get_base_mock_asset()
    asset5.purchase_value = Decimal('10000.0000')
    res5 = AssetService.calculate_operational_solar_depreciation(asset5, Decimal('24'))
    if res5 == Decimal('0.0000'): tests_passed += 1; print(" [OK] Test 5: Depreciable base <= 0 returns 0.0000")
    else: errors += 1; print(f" [FAIL] Test 5")

    # For posting tests, mock DB
    with patch('smart_agri.finance.models.FinancialLedger.objects.create') as mock_create, \
         patch('smart_agri.core.models.Asset.objects.select_for_update') as mock_select:
        
        mock_qs = MagicMock()
        mock_qs.get.return_value = get_base_mock_asset()
        mock_select.return_value = mock_qs
        user = MagicMock()

        # Test 6: post_solar_operational_depreciation creates exact 2 Ledger Entries
        res6 = AssetService.post_solar_operational_depreciation(asset, Decimal('24'), user)
        if mock_create.call_count == 2: tests_passed += 1; print(" [OK] Test 6: 2 Ledger entries correctly generated")
        else: errors += 1; print(" [FAIL] Test 6")

        dr_call = mock_create.call_args_list[0][1]
        # Test 7: DR account is 7000-DEP-EXP
        if dr_call['account_code'] == '7000-DEP-EXP' and dr_call['debit'] == res6: tests_passed += 1; print(" [OK] Test 7: DR account is 7000-DEP-EXP correctly")
        else: errors += 1; print(" [FAIL] Test 7")

        cr_call = mock_create.call_args_list[1][1]
        # Test 8: CR account is 1500-ACC-DEP
        if cr_call['account_code'] == '1500-ACC-DEP' and cr_call['credit'] == res6: tests_passed += 1; print(" [OK] Test 8: CR account is 1500-ACC-DEP correctly")
        else: errors += 1; print(" [FAIL] Test 8")

        # Test 9: truncates if exceeds remaining value
        mock_create.reset_mock()
        asset9 = get_base_mock_asset()
        asset9.accumulated_depreciation = Decimal('89990.0000') # 10 YER remaining
        mock_qs.get.return_value = get_base_mock_asset()
        mock_qs.get.return_value.accumulated_depreciation = Decimal('89990.0000')
        res9 = AssetService.post_solar_operational_depreciation(asset9, Decimal('24000'), user) # large hours
        if res9 == Decimal('10.0000'): tests_passed += 1; print(" [OK] Test 9: Amount correctly truncated at remaining base")
        else: errors += 1; print(f" [FAIL] Test 9: {res9}")

        # Test 10: updates accumulated_depreciation on the asset
        saved_asset = mock_qs.get.return_value
        if saved_asset.save.called: tests_passed += 1; print(" [OK] Test 10: Asset saved with updated accumulated_depreciation")
        else: errors += 1; print(" [FAIL] Test 10")

    print(f"\n=============================")
    print(f"Total passed: {tests_passed}/10")
    if errors > 0:
        print("STATUS: FAILED")
        sys.exit(1)
    else:
        print("STATUS: PASSED")
    sys.exit(0)

if __name__ == "__main__":
    run()
