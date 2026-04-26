import os
import sys
from decimal import Decimal
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")

import django
django.setup()

from smart_agri.core.services.harvest_service import HarvestService
from smart_agri.finance.models import FinancialLedger
from django.utils import timezone

def get_mock_activity():
    activity = MagicMock()
    activity.pk = 1
    activity.harvest_details.harvest_quantity = Decimal('100.0000')
    activity.harvest_details.product_id = 99
    activity.harvest_details.harvest_date = "2023-01-01"
    # product mock
    product = MagicMock()
    product.name = "Wheat"
    product.item = MagicMock()
    product.crop.max_yield_per_ha = Decimal('5.0')
    activity.product = product
    
    activity.crop_plan.area = Decimal('10.0')
    activity.crop_plan.farm = MagicMock()
    activity.log.farm.zakat_rule = "5_PERCENT"
    activity.log.log_date = "2023-01-01"
    activity.activity_date = "2023-01-01"
    activity.farm_id = 1
    activity.location = MagicMock()
    return activity

def run():
    errors = 0
    tests_passed = 0
    print("[AGRI-GUARDIAN] Axis 9: Sovereign Liabilities - Zakat Triggers")

    # T1: 5% Zakat calculation
    amt = HarvestService.calculate_zakat_due(Decimal("100"), "5_PERCENT")
    if amt == Decimal("5.0000"): tests_passed += 1; print(" [OK] T1: 5% zakat correctly calculated")
    else: errors += 1; print(" [FAIL] T1")

    # T2: 10% Zakat calculation
    amt2 = HarvestService.calculate_zakat_due(Decimal("100"), "10_PERCENT")
    if amt2 == Decimal("10.0000"): tests_passed += 1; print(" [OK] T2: 10% zakat correctly calculated")
    else: errors += 1; print(" [FAIL] T2")

    # T3: Zero harvest
    amt3 = HarvestService.calculate_zakat_due(Decimal("0"), "10_PERCENT")
    if amt3 == Decimal("0.0000"): tests_passed += 1; print(" [OK] T3: 0 zakat on 0 harvest")
    else: errors += 1; print(" [FAIL] T3")

    # For testing process_harvest, mock the DB checks
    with patch('smart_agri.core.models.CropProduct.objects.filter') as mock_cp, \
         patch('smart_agri.core.services.harvest_service.resolve_zakat_policy_for_harvest') as mock_policy, \
         patch('smart_agri.finance.models.FinancialLedger.objects.create') as mock_create, \
         patch('smart_agri.finance.models.FinancialLedger.objects.filter') as mock_filter, \
         patch('smart_agri.inventory.models.StockMovement.objects.filter') as mock_stock_filter, \
         patch('smart_agri.core.services.inventory_service.InventoryService.process_grn'), \
         patch('smart_agri.core.services.harvest_service.HarvestService._resolve_unit_cost') as mock_cost, \
         patch('smart_agri.core.services.sensitive_audit.log_sensitive_mutation'), \
         patch('smart_agri.core.models.HarvestLot.objects.create'), \
         patch('smart_agri.core.models.log.AuditLog.objects.create'):

        mock_filter.return_value.exists.return_value = False
        mock_stock_filter.return_value.exists.return_value = False
        mock_cost.return_value = Decimal("10.0000")

        mock_product = MagicMock()
        mock_product.item = MagicMock()
        mock_product.crop.max_yield_per_ha = Decimal('5.0')
        qs_mock = MagicMock()
        qs_mock.first.return_value = mock_product
        mock_cp.return_value = qs_mock

        mock_policy.return_value = None

        activity = get_mock_activity()
        user = MagicMock()

        HarvestService.process_harvest(activity, user)

        # Expected calls: Inventory Asset (DR), WIP (CR), Zakat Expense (DR), Zakat Payable (CR)
        calls = [c[1] for c in mock_create.call_args_list]
        
        has_dr = any(c.get('account_code') == '7100-ZAKAT-EXP' and c.get('debit') == Decimal('50.0000') for c in calls)
        if has_dr: tests_passed += 1; print(" [OK] T4: Zakat Expense (7100-ZAKAT-EXP) DR correctly posted")
        else: errors += 1; print(" [FAIL] T4")

        has_cr = any(c.get('account_code') == '2105-ZAKAT-PAY' and c.get('credit') == Decimal('50.0000') for c in calls)
        if has_cr: tests_passed += 1; print(" [OK] T5: Zakat Payable (2105-ZAKAT-PAY) CR correctly posted")
        else: errors += 1; print(" [FAIL] T5")

    print(f"\n=============================")
    print(f"Total passed: {tests_passed}/5")
    if errors > 0:
        print("STATUS: FAILED")
        sys.exit(1)
    else:
        print("STATUS: PASSED")
    sys.exit(0)

if __name__ == "__main__":
    run()
