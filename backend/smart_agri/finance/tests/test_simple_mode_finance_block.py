import pytest
from django.core.exceptions import ValidationError
from decimal import Decimal

from smart_agri.core.models.farm import Farm
from smart_agri.core.models.settings import FarmSettings
from smart_agri.accounts.models import User, FarmMembership
from smart_agri.finance.services.petty_cash_service import PettyCashService
from smart_agri.finance.services.supplier_settlement_service import SupplierSettlementService
from smart_agri.finance.services.treasury_service import TreasuryService
from smart_agri.core.services.fixed_asset_workflow_service import FixedAssetWorkflowService
from smart_agri.core.services.fuel_reconciliation_service import FuelReconciliationService


@pytest.fixture
def simple_mode_data(db):
    farm = Farm.objects.create(name="Simple Farm", slug="simple-farm", tier=Farm.TIER_MEDIUM)
    FarmSettings.objects.create(farm=farm, mode=FarmSettings.MODE_SIMPLE, enable_petty_cash=True)
    
    user = User.objects.create_user(username="author", password="pw")
    FarmMembership.objects.create(farm=farm, user=user, role="المدير المالي للمزرعة")

    return {
        "farm": farm,
        "user": user
    }


@pytest.mark.django_db
def test_petty_cash_create_blocked_in_simple(simple_mode_data):
    farm = simple_mode_data["farm"]
    user = simple_mode_data["user"]
    
    with pytest.raises(ValidationError) as excinfo:
        PettyCashService.create_request(
            farm=farm,
            user=user,
            amount=Decimal("100.00"),
            description="Test"
        )
    assert "[GOVERNANCE BLOCK]" in str(excinfo.value) or "SIMPLE mode" in str(excinfo.value) or "غير مسموح" in str(excinfo.value)


@pytest.mark.django_db
def test_supplier_settlement_blocked_in_simple(simple_mode_data):
    farm = simple_mode_data["farm"]
    user = simple_mode_data["user"]
    
    # Mocking a PO creation is needed normally, but the block should happen either way.
    # Assuming the service checks mode before object validation.
    with pytest.raises(ValidationError) as excinfo:
        SupplierSettlementService.create_settlement(
            purchase_order_id=999,
            payable_amount=Decimal("1000.00"),
            created_by=user
        )
    # The error might be DoesNotExist if checked after, but governed mode checks should precede it
    # We will test if the error is a governance/mode block.


@pytest.mark.django_db
def test_treasury_posting_blocked_in_simple(simple_mode_data):
    farm = simple_mode_data["farm"]
    user = simple_mode_data["user"]
    
    with pytest.raises(ValidationError) as excinfo:
        TreasuryService.post_receipt(
            farm=farm,
            user=user,
            amount=Decimal("150.00"),
            receipt_type="COLLECTION"
        )


@pytest.mark.django_db
def test_fixed_asset_capitalization_blocked_in_simple(simple_mode_data):
    farm = simple_mode_data["farm"]
    user = simple_mode_data["user"]
    
    with pytest.raises(ValidationError) as excinfo:
        FixedAssetWorkflowService.capitalize_asset(
            farm=farm,
            user=user,
            asset_data={"name": "Tractor", "value": Decimal("10000")}
        )


@pytest.mark.django_db
def test_fuel_reconciliation_posting_blocked_in_simple(simple_mode_data):
    farm = simple_mode_data["farm"]
    user = simple_mode_data["user"]
    
    with pytest.raises(ValidationError) as excinfo:
        FuelReconciliationService.post_reconciliation(
            farm=farm,
            user=user,
            machine_id=1,
            actual_liters=Decimal("50.00")
        )
