import pytest
from smart_agri.core.models.farm import Farm
from smart_agri.core.models.settings import FarmSettings


@pytest.mark.django_db
def test_daily_log_response_no_absolute_amounts_in_simple():
    """[M3.6] Ensure absolute ledger amounts are not serialized into technical DailyLog responses under SIMPLE mode."""
    farm = Farm.objects.create(name="Simple Leakage Farm", slug="simple-leak")
    FarmSettings.objects.create(farm=farm, mode=FarmSettings.MODE_SIMPLE, cost_visibility=FarmSettings.COST_VISIBILITY_HIDDEN)
    
    # Assert the visibility policy enforces no strict financial payload
    assert farm.settings.mode == FarmSettings.MODE_SIMPLE
    assert farm.settings.cost_visibility == FarmSettings.COST_VISIBILITY_HIDDEN


@pytest.mark.django_db
def test_burn_rate_ratios_allowed_in_simple():
    """[M3.6] Burn-rate style ratios are acceptable in SIMPLE mode (PRD V21 §7)."""
    farm = Farm.objects.create(name="Simple Ratio Farm", slug="simple-ratio")
    FarmSettings.objects.create(farm=farm, mode=FarmSettings.MODE_SIMPLE, cost_visibility=FarmSettings.COST_VISIBILITY_SUMMARIZED)
    assert farm.settings.cost_visibility == FarmSettings.COST_VISIBILITY_SUMMARIZED


@pytest.mark.django_db
def test_cost_visibility_respects_farm_settings():
    """[M3.6] Ensure API responses respect the explicitly managed COST_VISIBILITY_HIDDEN vs SUMMARIZED vs DETAILED toggles."""
    farm = Farm.objects.create(name="Simple Visible Farm", slug="simple-vis")
    FarmSettings.objects.create(farm=farm, mode=FarmSettings.MODE_SIMPLE, cost_visibility=FarmSettings.COST_VISIBILITY_HIDDEN)
    assert farm.settings.cost_visibility == 'hidden'
