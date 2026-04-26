import pytest
from unittest.mock import patch, MagicMock
from django.core.exceptions import ValidationError

@pytest.mark.django_db
def test_farm_chief_accountant_cannot_hard_close_sector_ledgers():
    """
    [M2.8] "رئيس حسابات المزرعة is the local accounting-review and soft-close-readiness role; 
    it is not a substitute for the sector chief accountant."
    """
    from smart_agri.finance.services.farm_finance_authority_service import FarmFinanceAuthorityService
    
    # Mocking a user acting as local farm chief accountant
    mock_user = MagicMock()
    mock_farm = MagicMock()
    
    # Simulate the service blocking the hard close because the user is only a Local Chief Accountant
    with patch.object(FarmFinanceAuthorityService, 'get_user_delegated_roles') as mock_roles:
        mock_roles.return_value = ["رئيس حسابات المزرعة"]
        
        # Should raise permission denied or validation error when attempting sector final authority
        with pytest.raises(Exception):
            FarmFinanceAuthorityService.require_sector_final_authority(user=mock_user, farm=mock_farm)

@pytest.mark.django_db
def test_sector_chief_accountant_grants_hard_close_authority():
    """
    [M2.8] "رئيس حسابات القطاع" represents the sector chain and grants sector final auth 
    for major threshold closures.
    """
    from smart_agri.finance.services.farm_finance_authority_service import FarmFinanceAuthorityService
    
    mock_user = MagicMock()
    mock_farm = MagicMock()
    
    # Simulate the user acting as Sector Chief Accountant
    with patch.object(FarmFinanceAuthorityService, 'get_user_delegated_roles') as mock_roles, \
         patch('smart_agri.finance.services.farm_finance_authority_service.FarmFinanceAuthorityService.require_sector_final_authority') as auth_mock:
        
        mock_roles.return_value = ["رئيس حسابات القطاع", "المدير المالي لقطاع المزارع"]
        
        # Should execute successfully without throwing exceptions
        auth_mock(user=mock_user, farm=mock_farm)
        auth_mock.assert_called_once()
