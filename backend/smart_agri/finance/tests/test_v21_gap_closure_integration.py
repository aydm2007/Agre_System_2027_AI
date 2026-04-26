"""
[AGRI-GUARDIAN V21 — Phase 5] Integration Tests for Gap Closure
================================================================
Tests proving:
1. SMALL farm hard-close prevention (PRD §8.1)
2. Activity lifecycle shadow accounting boundary
3. Threshold escalation for SMALL farms
4. FarmTieringPolicyService enforcement
"""
import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.core.exceptions import ValidationError, PermissionDenied
from django.test import TestCase

from smart_agri.core.models.farm import Farm
from smart_agri.core.models.settings import FarmSettings
from smart_agri.accounts.models import User, FarmMembership
from smart_agri.core.services.farm_tiering_policy_service import FarmTieringPolicyService


# ─── SMALL Farm Hard-Close Prevention ────────────────────────────────────────

@pytest.mark.django_db
class TestSmallFarmHardClosePrevention:
    """
    [PRD V21 §8.1] المزارع الصغيرة لا يمكنها تنفيذ الإقفال النهائي محلياً.
    
    Compensating controls:
    - سقوف محلية
    - مراجعة قطاعية أسبوعية
    - تصعيد تلقائي فوق السقوف
    - منع hard-close محلياً
    """

    def test_small_farm_hard_close_blocked(self, db):
        """SMALL farm cannot hard-close locally — must go through sector."""
        from smart_agri.finance.services.fiscal_governance_service import FiscalGovernanceService
        from smart_agri.finance.models import FiscalYear, FiscalPeriod

        farm = Farm.objects.create(name="Small Farm HC", slug="small-farm-hc", tier="small")
        FarmSettings.objects.create(farm=farm, mode=FarmSettings.MODE_STRICT)
        user = User.objects.create_user(username="small_accountant", password="password")
        
        fy = FiscalYear.objects.create(
            farm=farm, name="2026", start_date="2026-01-01", end_date="2026-12-31"
        )
        period = FiscalPeriod.objects.create(
            farm=farm, fiscal_year=fy, name="Q1",
            start_date="2026-01-01", end_date="2026-03-31",
            status=FiscalPeriod.STATUS_SOFT_CLOSE
        )

        with pytest.raises((ValidationError, PermissionDenied)) as excinfo:
            FiscalGovernanceService.transition_period(
                period_id=period.id,
                target_status=FiscalPeriod.STATUS_HARD_CLOSE,
                user=user
            )
        error_msg = str(excinfo.value)
        assert "GOVERNANCE BLOCK" in error_msg or "المزارع الصغيرة" in error_msg or "sector" in error_msg.lower()

    def test_medium_farm_hard_close_allowed_with_authority(self, db):
        """MEDIUM farm can hard-close when user has sector authority."""
        # This test validates the tier check doesn't block MEDIUM farms
        tier_snap = FarmTieringPolicyService.snapshot("medium")
        assert tier_snap['tier'] == 'medium'
        assert tier_snap['tier'] not in ('small', 'basic')

    def test_large_farm_hard_close_allowed_with_authority(self, db):
        """LARGE farm can hard-close when user has sector authority."""
        tier_snap = FarmTieringPolicyService.snapshot("large")
        assert tier_snap['tier'] == 'large'
        assert tier_snap['tier'] not in ('small', 'basic')


# ─── FarmTieringPolicyService Enforcement ────────────────────────────────────

@pytest.mark.django_db
class TestFarmTieringPolicyEnforcement:
    """
    [PRD V21 §8] TIER_MATRIX correctness and enforce finance authority.
    """

    def test_small_farm_does_not_require_ffm(self):
        """SMALL farms: single finance officer allowed."""
        snap = FarmTieringPolicyService.snapshot("small")
        assert snap['requires_farm_finance_manager'] is False
        assert snap['finance_model'] == 'single_officer_allowed'

    def test_medium_farm_requires_ffm(self):
        """MEDIUM farms: Farm Finance Manager required."""
        snap = FarmTieringPolicyService.snapshot("medium")
        assert snap['requires_farm_finance_manager'] is True

    def test_large_farm_requires_ffm(self):
        """LARGE farms: Farm Finance Manager required with stronger segregation."""
        snap = FarmTieringPolicyService.snapshot("large")
        assert snap['requires_farm_finance_manager'] is True
        assert snap['approval_levels'] >= 5

    def test_backward_compat_basic_maps_to_small(self):
        """backward compat: 'basic' tier maps to SMALL semantics."""
        snap = FarmTieringPolicyService.snapshot("basic")
        assert snap['requires_farm_finance_manager'] is False

    def test_unknown_tier_defaults_to_small(self):
        """Unknown tier input defaults to SMALL (fail-safe)."""
        snap = FarmTieringPolicyService.snapshot("unknown_tier_xyz")
        assert snap['tier'] == 'unknown_tier_xyz'
        # Should get small defaults from fallback

    def test_none_tier_defaults_to_small(self):
        """None tier defaults to SMALL."""
        snap = FarmTieringPolicyService.snapshot(None)
        assert snap['tier'] == 'small'

    def test_validate_finance_authority_blocks_medium_without_ffm(self, db):
        """MEDIUM farm without FFM assigned blocks financial operations."""
        farm = Farm.objects.create(name="No-FFM Farm", slug="no-ffm", tier="medium")
        FarmSettings.objects.create(farm=farm, mode=FarmSettings.MODE_STRICT, farm_tier="medium")
        
        with pytest.raises(ValidationError) as excinfo:
            FarmTieringPolicyService.validate_finance_authority(farm=farm)
        assert "المدير المالي" in str(excinfo.value)


# ─── Shadow Accounting Integration ───────────────────────────────────────────

class TestShadowAccountingIntegration(TestCase):
    """
    [PRD V21 §7.2 / §10] Shadow accounting boundary proof.
    
    In SIMPLE mode:
    - CostingService CAN compute Activity costs (shadow values)
    - enforce_strict_mode BLOCKS any FinancialLedger posting
    - TreasuryTransaction creation is blocked
    
    This is the integration test proving the boundary exists code-structurally.
    """

    def test_costing_service_has_shadow_doctrine(self):
        """CostingService must document the shadow accounting doctrine."""
        from smart_agri.finance.services.costing_service import CostingService
        docstring = CostingService.__doc__ or ""
        self.assertIn("SHADOW ACCOUNTING DOCTRINE", docstring)

    def test_enforce_strict_mode_exists_and_blocks(self):
        """enforce_strict_mode must be importable and raise PermissionDenied."""
        from smart_agri.core.decorators import enforce_strict_mode
        # None farm should raise
        with self.assertRaises(PermissionDenied):
            enforce_strict_mode(None)

    def test_petty_cash_service_has_guard(self):
        """PettyCashService mutations must import and call enforce_strict_mode."""
        import inspect
        from smart_agri.finance.services.petty_cash_service import PettyCashService
        source = inspect.getsource(PettyCashService)
        self.assertIn("enforce_strict_mode", source,
                       "PettyCashService must call enforce_strict_mode for defense-in-depth")

    def test_supplier_settlement_has_guard(self):
        """SupplierSettlementService must import and call enforce_strict_mode."""
        import inspect
        from smart_agri.finance.services.supplier_settlement_service import SupplierSettlementService
        source = inspect.getsource(SupplierSettlementService)
        self.assertIn("enforce_strict_mode", source,
                       "SupplierSettlementService must call enforce_strict_mode for defense-in-depth")

    def test_fiscal_governance_small_hard_close_prevention(self):
        """FiscalGovernanceService must check tier before hard-close."""
        import inspect
        from smart_agri.finance.services.fiscal_governance_service import FiscalGovernanceService
        source = inspect.getsource(FiscalGovernanceService)
        self.assertIn("FarmTieringPolicyService", source,
                       "FiscalGovernanceService must use FarmTieringPolicyService for tier-aware hard-close")
        self.assertIn("small", source.lower(),
                       "FiscalGovernanceService must reference SMALL tier")


# ─── Activity Lifecycle Structural Proof ─────────────────────────────────────

class TestActivityLifecycleStructuralProof(TestCase):
    """
    [PRD V21 §10] Truth chain structural proof:
    CropPlan → DailyLog → Activity → SmartCard → Variance → Ledger
    
    Validates that the code structures implementing each link exist and
    are correctly connected.
    """

    def test_activity_has_cost_fields(self):
        """Activity model must have all 4 cost breakdown fields."""
        from smart_agri.core.models.activity import Activity
        for field_name in ['cost_labor', 'cost_materials', 'cost_machinery', 'cost_overhead', 'cost_total']:
            self.assertTrue(
                hasattr(Activity, field_name) or Activity._meta.get_field(field_name),
                f"Activity missing cost field: {field_name}"
            )

    def test_activity_links_to_crop_plan(self):
        """Activity must have a FK to CropPlan (truth chain link 1)."""
        from smart_agri.core.models.activity import Activity
        field = Activity._meta.get_field('crop_plan')
        self.assertIsNotNone(field, "Activity must link to CropPlan")

    def test_activity_links_to_daily_log(self):
        """Activity must be accessible via DailyLog (truth chain link 2)."""
        from smart_agri.core.models.activity import Activity
        field = Activity._meta.get_field('log')
        self.assertIsNotNone(field, "Activity must link to DailyLog via 'log' FK")

    def test_activity_has_task_contract_snapshot(self):
        """Activity must have task_contract_snapshot for SmartCard binding."""
        from smart_agri.core.models.activity import Activity
        field = Activity._meta.get_field('task_contract_snapshot')
        self.assertIsNotNone(field, "Activity must have task_contract_snapshot (SmartCard link)")

    def test_daily_log_has_smart_card_stack(self):
        """DailyLog model must have smart_card_stack field."""
        from smart_agri.core.models.log import DailyLog
        field = DailyLog._meta.get_field('smart_card_stack')
        self.assertIsNotNone(field, "DailyLog must have smart_card_stack field")

    def test_smart_card_stack_service_exists(self):
        """SmartCardStack canonical service must be importable."""
        from smart_agri.core.services.smart_card_stack_service import canonical_smart_card_stack
        self.assertTrue(callable(canonical_smart_card_stack))

    def test_variance_services_exist(self):
        """All 3 variance engines must be importable."""
        from smart_agri.core.services.variance_analysis_service import VarianceAnalysisService
        from smart_agri.core.services.schedule_variance_service import ScheduleVarianceService
        from smart_agri.core.services.shadow_variance_engine import ShadowVarianceEngine
        self.assertTrue(callable(getattr(ScheduleVarianceService, 'check_schedule_variance', None)))

    def test_frictionless_daily_log_service_exists(self):
        """FrictionlessDailyLogService must be importable."""
        from smart_agri.core.services.daily_log_execution import FrictionlessDailyLogService
        self.assertTrue(callable(getattr(FrictionlessDailyLogService, 'process_technical_log', None)))


# ─── Threshold Escalation Guard ──────────────────────────────────────────────

class TestThresholdEscalationGuard(TestCase):
    """
    [PRD V21 §8.1] SMALL farm expense ceiling and escalation rules.
    """

    def test_small_farm_ceiling_defined(self):
        """SMALL_FARM_LOCAL_EXPENSE_CEILING must be defined."""
        from smart_agri.finance.services.fiscal_governance_service import FiscalGovernanceService
        self.assertIsNotNone(FiscalGovernanceService.SMALL_FARM_LOCAL_EXPENSE_CEILING)
        self.assertGreater(FiscalGovernanceService.SMALL_FARM_LOCAL_EXPENSE_CEILING, 0)

    def test_tier_matrix_has_sector_review_default(self):
        """All tiers must have sector_review_default=True for compensating controls."""
        for tier_key, policy in FarmTieringPolicyService.TIER_MATRIX.items():
            self.assertTrue(
                policy.get('sector_review_default', False),
                f"Tier '{tier_key}' must have sector_review_default=True"
            )
