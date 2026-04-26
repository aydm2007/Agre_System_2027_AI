import pytest
from smart_agri.accounts.models import User
from smart_agri.finance.services.approval_service import ApprovalGovernanceService
from django.core.exceptions import ValidationError

@pytest.mark.django_db
def test_farm_chief_accountant_cannot_do_sector_signoff():
    """
    ROLE_PERMISSION_MATRIX: رئيس حسابات المزرعة is local review only.
    Cannot perform sector accounting sign-off.
    """
    user = User.objects.create(username="farm_chief", role="رئيس حسابات المزرعة")
    
    # Mock or test the service directly if it checks roles
    # We will simulate the check that is expected in ApprovalGovernanceService
    assert not ApprovalGovernanceService.can_perform_role(user, "رئيس حسابات القطاع")

@pytest.mark.django_db
def test_sector_chief_accountant_can_do_reconciliation_signoff():
    """
    ROLE_PERMISSION_MATRIX: رئيس حسابات القطاع owns reconciliation sign-off.
    """
    user = User.objects.create(username="sector_chief", role="رئيس حسابات القطاع")
    assert ApprovalGovernanceService.can_perform_role(user, "رئيس حسابات القطاع")
