import pytest
from decimal import Decimal
from smart_agri.core.models.farm import Farm
from smart_agri.core.models.settings import FarmSettings
from smart_agri.core.models.planning import CropPlan
from smart_agri.core.models.activity import Activity
from smart_agri.core.models.report import VarianceAlert
from smart_agri.core.services.shadow_variance_engine import ShadowVarianceEngine

@pytest.fixture
def setup_farm_with_simple_mode():
    farm = Farm.objects.create(name="Simple Test Farm", slug="simple-test-farm", tier=Farm.TIER_SMALL)
    FarmSettings.objects.create(farm=farm, mode=FarmSettings.MODE_SIMPLE)
    return farm

@pytest.mark.django_db  
def test_simple_mode_creates_shadow_variance(setup_farm_with_simple_mode):
    """
    PRD §4.4: SIMPLE maintains Shadow Accounting.
    When actual cost exceeds planned cost, a VarianceAlert is created automatically.
    """
    farm = setup_farm_with_simple_mode
    
    crop_plan = CropPlan.objects.create(
        farm=farm,
        name="Test Wheat Plan",
        start_date="2026-01-01",
        end_date="2026-12-31"
    )
    
    planned_cost = Decimal('1000.00')
    actual_cost = Decimal('1500.00') # 50% Overrun
    
    result = ShadowVarianceEngine.audit_execution_cost(
        farm=farm,
        activity_name="Fertilization",
        actual_cost=actual_cost,
        planned_cost=planned_cost,
        category=VarianceAlert.CATEGORY_BUDGET_OVERRUN
    )
    
    assert "CREATED" in result
    
    alert_exists = VarianceAlert.objects.filter(farm=farm, category=VarianceAlert.CATEGORY_BUDGET_OVERRUN).exists()
    assert alert_exists, "VarianceAlert should be created by ShadowVarianceEngine in SIMPLE mode."
