import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from smart_agri.core.models.farm import Farm
from smart_agri.core.models.settings import FarmSettings
from smart_agri.accounts.models import User, FarmMembership

@pytest.fixture
def setup_farm_with_simple_mode():
    farm = Farm.objects.create(name="Simple Test Farm", slug="simple-test-farm", tier=Farm.TIER_SMALL)
    FarmSettings.objects.create(farm=farm, mode=FarmSettings.MODE_SIMPLE, enable_petty_cash=True)
    return farm

@pytest.fixture
def create_superuser():
    def _create_user():
        user = User.objects.create_superuser(username="superadmin", email="admin@test.com", password="password")
        return user
    return _create_user

@pytest.mark.django_db
def test_admin_cannot_bypass_simple_mode_for_finance(setup_farm_with_simple_mode, create_superuser):
    """
    AGENTS Rule 25: Admin convenience must not silently reopen
    full financial route trees in SIMPLE.
    Even superuser should be blocked by StrictModeRequired.
    """
    farm = setup_farm_with_simple_mode
    user = create_superuser()
    
    # Assign membership to prevent basic 403 due to missing farm mapping
    FarmMembership.objects.create(farm=farm, user=user)

    client = APIClient()
    client.force_authenticate(user=user)
    
    # Attempt to hit the Petty Cash Request endpoint 
    url = "/api/v1/finance/petty-cash-requests/"
    payload = {
        "farm": farm.id,
        "amount": "500.00",
        "description": "Admin test simple mode breach"
    }
    
    response = client.post(url, payload, HTTP_X_IDEMPOTENCY_KEY="test-1234")
    
    # It must be 403 Forbidden because of StrictModeRequired, despite is_superuser=True
    assert response.status_code == 403
    assert "STRICT" in str(response.data) or "block" in str(response.data).lower() or "permission" in str(response.data).lower()
