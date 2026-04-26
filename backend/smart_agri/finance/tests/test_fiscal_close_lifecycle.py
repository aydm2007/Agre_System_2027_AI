import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from smart_agri.core.models.farm import Farm
from smart_agri.accounts.models import User, FarmMembership
from smart_agri.finance.models import FiscalYear, FiscalPeriod
from smart_agri.finance.services.fiscal_governance_service import FiscalGovernanceService
from smart_agri.core.models.log import AuditLog

@pytest.fixture
def setup_fiscal_data(db):
    farm = Farm.objects.create(name="Fiscal Test Farm", slug="fiscal-test-farm", tier=Farm.TIER_LARGE)
    # Enable STRICT mode
    from smart_agri.core.models.settings import FarmSettings
    # We must assign FFM first for LARGE farm to enter STRICT mode!
    ffm_user = User.objects.create_user(username="ffm", password="password")
    FarmMembership.objects.create(farm=farm, user=ffm_user, role="المدير المالي للمزرعة")
    FarmSettings.objects.create(farm=farm, mode=FarmSettings.MODE_STRICT)

    sector_director = User.objects.create_user(username="director", password="password")
    FarmMembership.objects.create(farm=farm, user=sector_director, role="مدير القطاع")

    normal_user = User.objects.create_user(username="normal", password="password")
    FarmMembership.objects.create(farm=farm, user=normal_user, role="مهندس زراعي")

    fy = FiscalYear.objects.create(
        farm=farm,
        name="2026",
        start_date=timezone.now().date(),
        end_date=timezone.now().date() + timedelta(days=365),
        status='OPEN',
        is_closed=False
    )
    period = FiscalPeriod.objects.create(
        fiscal_year=fy,
        farm=farm,
        name="Jan 2026",
        start_date=timezone.now().date(),
        end_date=timezone.now().date() + timedelta(days=30),
        status=FiscalPeriod.STATUS_OPEN
    )

    return {
        "farm": farm,
        "period": period,
        "ffm_user": ffm_user,
        "sector_director": sector_director,
        "normal_user": normal_user
    }

@pytest.mark.django_db
def test_soft_close_requires_strict_authority(setup_fiscal_data):
    """
    Normal user cannot soft-close. FFM can soft-close.
    """
    data = setup_fiscal_data
    
    with pytest.raises(ValidationError) as excinfo:
        FiscalGovernanceService.transition_period(
            period_id=data["period"].id,
            target_status=FiscalPeriod.STATUS_SOFT_CLOSE,
            user=data["normal_user"]
        )
    assert "يتطلب صلاحية مالية" in str(excinfo.value) or "STRICT" in str(excinfo.value)

    # FFM should succeed
    period = FiscalGovernanceService.transition_period(
        period_id=data["period"].id,
        target_status=FiscalPeriod.STATUS_SOFT_CLOSE,
        user=data["ffm_user"]
    )
    assert period.status == FiscalPeriod.STATUS_SOFT_CLOSE

@pytest.mark.django_db
def test_hard_close_requires_sector_authority(setup_fiscal_data):
    """
    FFM cannot hard-close. Sector Director can hard-close.
    """
    data = setup_fiscal_data
    # First soft close
    FiscalGovernanceService.transition_period(
        period_id=data["period"].id,
        target_status=FiscalPeriod.STATUS_SOFT_CLOSE,
        user=data["ffm_user"]
    )
    
    with pytest.raises(ValidationError) as excinfo:
        FiscalGovernanceService.transition_period(
            period_id=data["period"].id,
            target_status=FiscalPeriod.STATUS_HARD_CLOSE,
            user=data["ffm_user"]
        )
    assert "اعتماداً قطاعياً نهائياً" in str(excinfo.value) or "Sector" in str(excinfo.value)

    # Sector Director should succeed
    period = FiscalGovernanceService.transition_period(
        period_id=data["period"].id,
        target_status=FiscalPeriod.STATUS_HARD_CLOSE,
        user=data["sector_director"]
    )
    assert period.status == FiscalPeriod.STATUS_HARD_CLOSE

@pytest.mark.django_db
def test_reopen_requires_narrative_and_logs(setup_fiscal_data):
    """
    Reopen requires sector authority, a valid reason, and creates an AuditLog.
    """
    data = setup_fiscal_data
    FiscalGovernanceService.transition_period(
        period_id=data["period"].id,
        target_status=FiscalPeriod.STATUS_SOFT_CLOSE,
        user=data["sector_director"]
    )
    FiscalGovernanceService.transition_period(
        period_id=data["period"].id,
        target_status=FiscalPeriod.STATUS_HARD_CLOSE,
        user=data["sector_director"]
    )

    with pytest.raises(ValidationError) as excinfo:
        FiscalGovernanceService.reopen_period(
            period_id=data["period"].id,
            user=data["sector_director"],
            reason=""
        )
    assert "reason is required" in str(excinfo.value).lower()

    with pytest.raises(ValidationError) as excinfo:
        FiscalGovernanceService.reopen_period(
            period_id=data["period"].id,
            user=data["ffm_user"],
            reason="Mistake in ledger"
        )
    assert "اعتماداً قطاعياً نهائياً" in str(excinfo.value) or "Sector" in str(excinfo.value)

    # Valid reopen
    period = FiscalGovernanceService.reopen_period(
        period_id=data["period"].id,
        user=data["sector_director"],
        reason="Auditor requested adjustment"
    )
    assert period.status == FiscalPeriod.STATUS_OPEN
    assert period._allow_reopen == True
    
    # Check AuditLog
    log = AuditLog.objects.filter(action="FISCAL_PERIOD_REOPEN").last()
    assert log is not None
    assert "Auditor requested adjustment" in log.notes
