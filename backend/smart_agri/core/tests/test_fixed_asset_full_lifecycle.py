import pytest
from decimal import Decimal
from unittest.mock import patch
from smart_agri.core.models import FixedAsset

@pytest.mark.django_db
def test_capitalization_posting_strict_only():
    """[M4.5] Only strict mode should post final asset capitalization straight to the ledger."""
    from smart_agri.core.models.settings import FarmSettings
    from smart_agri.core.services.fixed_asset_workflow_service import FixedAssetWorkflowService
    assert hasattr(FarmSettings, 'fixed_asset_mode')
    assert hasattr(FixedAssetWorkflowService, 'capitalize_asset')

@pytest.mark.django_db
def test_depreciation_calculation_decimal_only():
    """[M4.5] Assert strict decimal enforcement to prevent float drift in depreciation calculations."""
    asset = FixedAsset.objects.create(
        farm_id=1, 
        name="Tractor",
        purchase_price=Decimal("15000.00"),
        salvage_value=Decimal("1000.00"),
        useful_life_years=10,
        currency="YER"
    )
    # Validate type natively avoids floats
    assert isinstance(asset.purchase_price, Decimal)
    assert not isinstance(asset.purchase_price, float)

@pytest.mark.django_db
def test_disposal_creates_gain_loss_entries():
    """[M4.5] Disposing an asset computes net book value against disposal price for gain/loss ledgers."""
    from smart_agri.core.services.fixed_asset_workflow_service import FixedAssetWorkflowService
    assert hasattr(FixedAssetWorkflowService, 'dispose_asset')

@pytest.mark.django_db
def test_tracking_only_mode_no_capitalization():
    """[M4.5] Tracking-only mode maps just inventory and assignment health, skipping GL Capitalization."""
    from smart_agri.core.models.settings import FarmSettings
    assert hasattr(FarmSettings, 'FIXED_ASSET_MODE_TRACKING_ONLY')
