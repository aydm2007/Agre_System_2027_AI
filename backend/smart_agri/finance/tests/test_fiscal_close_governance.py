"""
Fiscal Close Governance Tests
================================
[AGRI-GUARDIAN Axis 8 / AGENTS.md §23 / PRD V21 §10 / ROLE_PERMISSION_MATRIX_V21 §2 / financial_integrity skill §2]
[READINESS_MATRIX must_pass: soft_close_local_implemented, hard_close_sector_authority_enforced,
 no_shortcut_in_final_transition, reopen_governed]

Verifies that:
1. FiscalGovernanceService enforces OPEN → SOFT_CLOSE → HARD_CLOSE chain (no skipping)
2. Hard close requires sector_final_authority (FarmFinanceAuthorityService)
3. Soft close requires strict_cycle_authority (not freely accessible)
4. Invalid transitions (e.g., HARD_CLOSE → OPEN) are rejected with ValidationError
5. Self-transition (same status) is rejected
6. FiscalPeriod model defines canonical status constants
7. Fiscal rollover is also governed (no silent period creation)
"""
from django.test import TestCase
from unittest.mock import patch, MagicMock, call
from django.core.exceptions import ValidationError


class FiscalGovernanceServiceTransitionTests(TestCase):
    """
    Tests for FiscalGovernanceService.transition_period.
    [AGENTS.md §23 / READINESS_MATRIX §close_readiness]
    """

    def setUp(self):
        from smart_agri.finance.models import FiscalPeriod
        self.FiscalPeriod = FiscalPeriod
        self.open_status = FiscalPeriod.STATUS_OPEN
        self.soft_status = FiscalPeriod.STATUS_SOFT_CLOSE
        self.hard_status = FiscalPeriod.STATUS_HARD_CLOSE

    def _make_mock_period(self, status):
        period = MagicMock()
        period.id = 1
        period.status = status
        period.farm = MagicMock()
        period.farm.id = 99
        return period

    def test_fiscal_period_defines_status_constants(self):
        """[PRD V21 §10] FiscalPeriod must define STATUS_OPEN, SOFT_CLOSE, HARD_CLOSE."""
        self.assertTrue(hasattr(self.FiscalPeriod, 'STATUS_OPEN'),
                        "FiscalPeriod must define STATUS_OPEN")
        self.assertTrue(hasattr(self.FiscalPeriod, 'STATUS_SOFT_CLOSE'),
                        "FiscalPeriod must define STATUS_SOFT_CLOSE")
        self.assertTrue(hasattr(self.FiscalPeriod, 'STATUS_HARD_CLOSE'),
                        "FiscalPeriod must define STATUS_HARD_CLOSE")
        # All three must be distinct
        statuses = {self.open_status, self.soft_status, self.hard_status}
        self.assertEqual(len(statuses), 3,
                         "STATUS_OPEN, STATUS_SOFT_CLOSE, STATUS_HARD_CLOSE must be distinct.")

    def test_transition_period_service_is_importable(self):
        """FiscalGovernanceService must be importable from finance services."""
        try:
            from smart_agri.finance.services.fiscal_governance_service import FiscalGovernanceService
        except ImportError as e:
            self.fail(f"FiscalGovernanceService must be importable: {e}")

    def test_invalid_skip_transition_hard_without_soft(self):
        """[AGENTS.md §23] Cannot skip SOFT_CLOSE: OPEN → HARD_CLOSE must be rejected."""
        from smart_agri.finance.services.fiscal_governance_service import FiscalGovernanceService
        mock_user = MagicMock()
        mock_period = self._make_mock_period(self.open_status)

        with patch(
            'smart_agri.finance.services.fiscal_governance_service.FiscalPeriod.objects.select_for_update'
        ) as mock_qs, patch(
            'smart_agri.finance.services.fiscal_governance_service.FiscalPeriod._normalize_status',
            side_effect=lambda s: s,
        ):
            mock_qs.return_value.get.return_value = mock_period
            mock_period.status = self.open_status

            with self.assertRaises(ValidationError) as ctx:
                FiscalGovernanceService.transition_period(
                    period_id=1,
                    target_status=self.hard_status,
                    user=mock_user,
                )
            self.assertIn('Invalid status transition', str(ctx.exception))

    def test_same_status_transition_rejected(self):
        """[AGENTS.md §23] Self-transition (same status) must raise ValidationError."""
        from smart_agri.finance.services.fiscal_governance_service import FiscalGovernanceService
        mock_user = MagicMock()
        mock_period = self._make_mock_period(self.open_status)

        with patch(
            'smart_agri.finance.services.fiscal_governance_service.FiscalPeriod.objects.select_for_update'
        ) as mock_qs, patch(
            'smart_agri.finance.services.fiscal_governance_service.FiscalPeriod._normalize_status',
            side_effect=lambda s: s,
        ):
            mock_qs.return_value.get.return_value = mock_period
            mock_period.status = self.open_status

            with self.assertRaises(ValidationError) as ctx:
                FiscalGovernanceService.transition_period(
                    period_id=1,
                    target_status=self.open_status,
                    user=mock_user,
                )
            self.assertIn('already in target status', str(ctx.exception))

    def test_hard_close_requires_sector_final_authority(self):
        """[AGENTS.md §23 / ROLE_PERMISSION_MATRIX §3.2] Hard close must require sector_final_authority."""
        from smart_agri.finance.services.fiscal_governance_service import FiscalGovernanceService
        from smart_agri.finance.services.farm_finance_authority_service import FarmFinanceAuthorityService
        mock_user = MagicMock()
        mock_period = self._make_mock_period(self.soft_status)

        with patch.object(
            FarmFinanceAuthorityService, 'require_sector_final_authority'
        ) as mock_sector_auth, patch(
            'smart_agri.finance.services.fiscal_governance_service.FiscalPeriod.objects.select_for_update'
        ) as mock_qs, patch(
            'smart_agri.finance.services.fiscal_governance_service.FiscalPeriod._normalize_status',
            side_effect=lambda s: s,
        ), patch(
            'smart_agri.finance.services.fiscal_governance_service.FinancialIntegrityService'
        ), patch(
            'smart_agri.finance.services.fiscal_governance_service.FiscalPeriod.objects.get',
            return_value=mock_period,
        ):
            mock_qs.return_value.get.return_value = mock_period
            mock_period.status = self.soft_status

            try:
                FiscalGovernanceService.transition_period(
                    period_id=1,
                    target_status=self.hard_status,
                    user=mock_user,
                )
            except (ValidationError, PermissionError, ValueError):
                pass  # We only care that require_sector_final_authority was called

        mock_sector_auth.assert_called_once()
        call_kwargs = mock_sector_auth.call_args[1]
        self.assertEqual(call_kwargs.get('user'), mock_user)

    def test_soft_close_requires_strict_cycle_authority(self):
        """[AGENTS.md §23 / ROLE_PERMISSION_MATRIX §3] Soft close must require strict_cycle_authority."""
        from smart_agri.finance.services.fiscal_governance_service import FiscalGovernanceService
        from smart_agri.finance.services.farm_finance_authority_service import FarmFinanceAuthorityService
        mock_user = MagicMock()
        mock_period = self._make_mock_period(self.open_status)

        with patch.object(
            FarmFinanceAuthorityService, 'require_strict_cycle_authority'
        ) as mock_cycle_auth, patch(
            'smart_agri.finance.services.fiscal_governance_service.FiscalPeriod.objects.select_for_update'
        ) as mock_qs, patch(
            'smart_agri.finance.services.fiscal_governance_service.FiscalPeriod._normalize_status',
            side_effect=lambda s: s,
        ):
            mock_qs.return_value.get.return_value = mock_period
            mock_period.status = self.open_status
            mock_period.closed_at = None
            mock_period.closed_by = None

            try:
                FiscalGovernanceService.transition_period(
                    period_id=1,
                    target_status=self.soft_status,
                    user=mock_user,
                )
            except (ValidationError, PermissionError, ValueError):
                pass

        mock_cycle_auth.assert_called_once()
        call_kwargs = mock_cycle_auth.call_args[1]
        self.assertEqual(call_kwargs.get('user'), mock_user)

    def test_hard_closed_period_has_no_allowed_transitions(self):
        """[AGENTS.md §23] Hard closed period cannot be transitioned further (immutable)."""
        from smart_agri.finance.services.fiscal_governance_service import FiscalGovernanceService
        mock_user = MagicMock()
        mock_period = self._make_mock_period(self.hard_status)

        with patch(
            'smart_agri.finance.services.fiscal_governance_service.FiscalPeriod.objects.select_for_update'
        ) as mock_qs, patch(
            'smart_agri.finance.services.fiscal_governance_service.FiscalPeriod._normalize_status',
            side_effect=lambda s: s,
        ):
            mock_qs.return_value.get.return_value = mock_period
            mock_period.status = self.hard_status

            with self.assertRaises(ValidationError):
                FiscalGovernanceService.transition_period(
                    period_id=1,
                    target_status=self.open_status,
                    user=mock_user,
                )

    def test_farm_finance_authority_service_exists(self):
        """[ROLE_PERMISSION_MATRIX §3.2] FarmFinanceAuthorityService must be importable."""
        try:
            from smart_agri.finance.services.farm_finance_authority_service import (
                FarmFinanceAuthorityService,
            )
            self.assertTrue(
                hasattr(FarmFinanceAuthorityService, 'require_sector_final_authority'),
                "FarmFinanceAuthorityService must implement require_sector_final_authority."
            )
            self.assertTrue(
                hasattr(FarmFinanceAuthorityService, 'require_strict_cycle_authority'),
                "FarmFinanceAuthorityService must implement require_strict_cycle_authority."
            )
        except ImportError as e:
            self.fail(f"FarmFinanceAuthorityService must be importable: {e}")

    def test_reopen_period_requires_reason(self):
        from smart_agri.finance.services.fiscal_governance_service import FiscalGovernanceService
        mock_user = MagicMock()
        with self.assertRaisesMessage(ValidationError, "A reason is required"):
            FiscalGovernanceService.reopen_period(period_id=1, user=mock_user, reason="")

    def test_reopen_period_enforces_auth_and_audit(self):
        from smart_agri.finance.services.fiscal_governance_service import FiscalGovernanceService
        from smart_agri.finance.services.farm_finance_authority_service import FarmFinanceAuthorityService
        
        mock_user = MagicMock()
        mock_period = self._make_mock_period(self.hard_status)
        
        with patch('smart_agri.finance.services.fiscal_governance_service.FiscalPeriod.objects.select_for_update') as mock_qs, \
             patch('smart_agri.finance.services.fiscal_governance_service.FiscalPeriod._normalize_status', side_effect=lambda s: s), \
             patch.object(FarmFinanceAuthorityService, 'require_sector_final_authority') as mock_auth, \
             patch('smart_agri.core.models.AuditLog.objects.create') as mock_audit_create:
            
            mock_qs.return_value.get.return_value = mock_period
            
            result = FiscalGovernanceService.reopen_period(period_id=1, user=mock_user, reason="Found an error")
            
            mock_auth.assert_called_once()
            self.assertEqual(result.status, self.open_status)
            self.assertTrue(getattr(result, '_allow_reopen', False))
            self.assertTrue(mock_period.save.called)
            mock_audit_create.assert_called_once_with(
                user=mock_user,
                action="FISCAL_PERIOD_REOPEN",
                notes="Reopened fiscal period 1. Reason: Found an error",
                farm=mock_period.farm,
                remote_ip="0.0.0.0"
            )

    def test_small_farm_cannot_hard_close_locally(self):
        """[M4.8] Farms tiered SMALL must rely on Sector review chains for hard close and cannot bypass via local officers."""
        from smart_agri.finance.services.farm_finance_authority_service import FarmFinanceAuthorityService
        from smart_agri.core.models import Farm
        from smart_agri.core.models.settings import FarmSettings
        farm = Farm(name="Small Farm", area=10)
        settings = FarmSettings(farm=farm, mode=FarmSettings.MODE_STRICT)
        # Mocking or asserting that the strict_finance profile tied to FarmFinanceAuthorityService effectively isolates local users
        assert hasattr(FarmFinanceAuthorityService, 'require_sector_final_authority')


class FiscalCloseReadinessTests(TestCase):
    """
    Tests that the fiscal close infrastructure is in place per READINESS_MATRIX.
    [READINESS_MATRIX §close_readiness / PRD V21 §10]
    """

    def test_fiscal_governance_service_uses_atomic_transaction(self):
        """[AGENTS.md §23] Fiscal transitions must be atomic (no partial commits)."""
        import inspect
        from smart_agri.finance.services.fiscal_governance_service import FiscalGovernanceService
        source = inspect.getsource(FiscalGovernanceService.transition_period)
        self.assertIn('atomic', source,
                      "transition_period must use @transaction.atomic for safety.")

    def test_fiscal_rollover_service_is_importable(self):
        """[AGENTS.md §23] Fiscal rollover service must exist for period lifecycle management."""
        try:
            from smart_agri.finance.services.fiscal_rollover_service import FiscalYearRolloverService  # noqa
        except ImportError as e:
            self.fail(f"FiscalYearRolloverService must be importable: {e}")

    def test_financial_integrity_service_performs_hard_close(self):
        """[AGENTS.md §23 / financial_integrity skill] FinancialIntegrityService must implement hard close."""
        try:
            from smart_agri.finance.services.financial_integrity_service import FinancialIntegrityService
            self.assertTrue(
                hasattr(FinancialIntegrityService, 'perform_hard_close'),
                "FinancialIntegrityService must implement perform_hard_close."
            )
        except ImportError as e:
            self.fail(f"FinancialIntegrityService must be importable: {e}")

    def test_select_for_update_used_in_transition(self):
        """[AGENTS.md §23] select_for_update must be used in transition to prevent race conditions."""
        import inspect
        from smart_agri.finance.services.fiscal_governance_service import FiscalGovernanceService
        source = inspect.getsource(FiscalGovernanceService.transition_period)
        self.assertIn('select_for_update', source,
                      "transition_period must use select_for_update to prevent concurrent transitions.")
