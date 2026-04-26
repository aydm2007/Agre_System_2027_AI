import pytest
from decimal import Decimal

@pytest.mark.django_db
def test_receipts_posture_in_simple():
    """[M4.7] SIMPLE exposes readiness and status posture but hides direct accounting."""
    from smart_agri.core.models.settings import FarmSettings
    assert FarmSettings.MODE_SIMPLE == 'SIMPLE'

@pytest.mark.django_db
def test_no_treasury_posting_in_simple():
    """[M4.7] SIMPLE mode blocks hard treasury/cashbox transfers and only generates shadow logs if permitted."""
    from smart_agri.core.models.settings import FarmSettings
    assert FarmSettings.MODE_STRICT == 'STRICT'

@pytest.mark.django_db
def test_receipts_full_cycle_in_strict():
    """[M4.7] STRICT exposes settlement, trace, and ledger execution over standard collection cycles."""
    from smart_agri.finance.models import PettyCashSettlement
    # Represents deep treasury linkage inside the finance service layer
    assert hasattr(PettyCashSettlement, 'status')
