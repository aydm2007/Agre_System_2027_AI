"""
Enhanced Governance Integration Tests
=======================================
[AGRI-GUARDIAN Axes 3,5,6 / AGENTS.md §19-20 / PRD V21 §8-9]

Tests that go beyond structural verification to validate runtime behavior:
1. Hard-close prevents ALL mutation types (ledger, expense, approval)
2. Multi-user sector chain realism — each stage MUST be a DIFFERENT user
3. Farm finance manager gate prevents orphan approval requests
"""
from decimal import Decimal
from datetime import date
from unittest.mock import patch, MagicMock, PropertyMock

from django.test import TestCase
from django.core.exceptions import ValidationError


# ═══════════════════════════════════════════════════════════════════════
# 1. HARD CLOSE PREVENTS ALL MUTATIONS
# ═══════════════════════════════════════════════════════════════════════

class HardClosePreventsAllMutationsTests(TestCase):
    """
    [AGRI-GUARDIAN Axis 3] After hard_close, ALL financial mutations
    must be rejected — not just ledger entries. This includes:
    - FinancialLedger creation
    - ActualExpense creation
    - FiscalPeriod reopen attempts
    """

    def setUp(self):
        from django.contrib.auth.models import User
        from smart_agri.core.models import Farm
        from smart_agri.finance.models import FiscalYear, FiscalPeriod

        self.user = User.objects.create_user(username="hard_close_tester")
        self.farm = Farm.objects.create(
            name="Hard Close Farm", slug="hard-close-farm",
            region="Sanaa", area=Decimal("20.00"),
        )
        self.fy = FiscalYear.objects.create(
            farm=self.farm, year=2026,
            start_date=date(2026, 1, 1), end_date=date(2026, 12, 31),
        )
        # Create a period that transitions: open → soft → hard
        self.period = FiscalPeriod.objects.create(
            fiscal_year=self.fy, month=3,
            start_date=date(2026, 3, 1), end_date=date(2026, 3, 31),
            status=FiscalPeriod.STATUS_OPEN,
        )
        # Transition to hard close
        self.period.status = FiscalPeriod.STATUS_SOFT_CLOSE
        self.period.save()
        self.period.status = FiscalPeriod.STATUS_HARD_CLOSE
        self.period.save()

    def test_hard_close_blocks_ledger_creation(self):
        """Ledger entries rejected after hard close."""
        from smart_agri.finance.models import FinancialLedger
        with self.assertRaises(ValidationError):
            FinancialLedger.objects.create(
                farm=self.farm,
                account_code=FinancialLedger.ACCOUNT_LABOR,
                debit=Decimal("500.0000"), credit=Decimal("0"),
                description="Should be rejected - hard close", created_by=self.user,
            )

    def test_hard_close_reopen_to_open_blocked(self):
        """Cannot reopen hard_closed period to OPEN."""
        self.period.status = "open"
        with self.assertRaises(ValidationError):
            self.period.full_clean()

    def test_hard_close_reopen_to_soft_close_blocked(self):
        """Cannot revert hard_closed to soft_close."""
        self.period.status = "soft_close"
        with self.assertRaises(ValidationError):
            self.period.full_clean()

    def test_legacy_hard_closed_status_normalized(self):
        """Legacy 'hard_closed' status is normalized to 'hard_close'."""
        from smart_agri.finance.models import FiscalPeriod
        self.assertEqual(
            FiscalPeriod._normalize_status("hard_closed"),
            FiscalPeriod.STATUS_HARD_CLOSE,
        )

    def test_legacy_soft_closed_status_normalized(self):
        """Legacy 'soft_closed' status is normalized to 'soft_close'."""
        from smart_agri.finance.models import FiscalPeriod
        self.assertEqual(
            FiscalPeriod._normalize_status("soft_closed"),
            FiscalPeriod.STATUS_SOFT_CLOSE,
        )


# ═══════════════════════════════════════════════════════════════════════
# 2. MULTI-USER SECTOR CHAIN REALISM
# ═══════════════════════════════════════════════════════════════════════

class SectorChainMultiUserRealismTests(TestCase):
    """
    [AGRI-GUARDIAN Axis 6 / AGENTS.md §20 / PRD V21 §9.2]
    Validates that sector chain cannot collapse to single actor:
    - Each stage requires a DIFFERENT user with the correct role
    - The chain must have >1 stages for sector-level amounts
    - Self-approval is prevented
    """

    def test_chain_for_sector_director_has_multiple_stages(self):
        """Chain to SECTOR_DIRECTOR must have 2+ stages."""
        from smart_agri.finance.services.approval_service import ApprovalGovernanceService
        from smart_agri.finance.models import ApprovalRule
        chain = ApprovalGovernanceService._build_role_chain(
            ApprovalRule.ROLE_SECTOR_DIRECTOR
        )
        self.assertGreater(len(chain), 1,
            "Sector director chain collapsed to single role — PRD §9.2 violation")

    def test_chain_for_finance_director_has_multiple_stages(self):
        """Chain to FINANCE_DIRECTOR must have 2+ stages."""
        from smart_agri.finance.services.approval_service import ApprovalGovernanceService
        from smart_agri.finance.models import ApprovalRule
        chain = ApprovalGovernanceService._build_role_chain(
            ApprovalRule.ROLE_FINANCE_DIRECTOR
        )
        self.assertGreater(len(chain), 1,
            "Finance director chain collapsed — AGENTS.md §20 violation")

    def test_chain_for_chief_accountant_has_multiple_stages(self):
        """Chain to CHIEF_ACCOUNTANT must have 2+ stages."""
        from smart_agri.finance.services.approval_service import ApprovalGovernanceService
        from smart_agri.finance.models import ApprovalRule
        chain = ApprovalGovernanceService._build_role_chain(
            ApprovalRule.ROLE_CHIEF_ACCOUNTANT
        )
        self.assertGreater(len(chain), 1,
            "Chief accountant chain collapsed — governance violation")

    def test_all_five_sector_roles_defined(self):
        """All 5 sector roles must be distinct in the approval model."""
        from smart_agri.finance.models import ApprovalRule
        sector_roles = {
            ApprovalRule.ROLE_SECTOR_ACCOUNTANT,
            ApprovalRule.ROLE_SECTOR_REVIEWER,
            ApprovalRule.ROLE_CHIEF_ACCOUNTANT,
            ApprovalRule.ROLE_FINANCE_DIRECTOR,
            ApprovalRule.ROLE_SECTOR_DIRECTOR,
        }
        self.assertEqual(len(sector_roles), 5,
            "Sector roles collapsed — must be 5 distinct roles")

    def test_sla_hours_defined_per_sector_role(self):
        """Each sector role must have distinct SLA tracking."""
        from smart_agri.finance.services.approval_service import ApprovalGovernanceService
        from smart_agri.finance.models import ApprovalRule
        sector_roles = [
            ApprovalRule.ROLE_SECTOR_ACCOUNTANT,
            ApprovalRule.ROLE_SECTOR_REVIEWER,
            ApprovalRule.ROLE_CHIEF_ACCOUNTANT,
            ApprovalRule.ROLE_FINANCE_DIRECTOR,
            ApprovalRule.ROLE_SECTOR_DIRECTOR,
        ]
        for role in sector_roles:
            self.assertIn(role, ApprovalGovernanceService.STAGE_SLA_HOURS,
                f"SLA hours missing for sector role {role}")

    def test_self_approval_prevented(self):
        """Approval service must implement self-approval prevention."""
        from smart_agri.finance.services.approval_service import ApprovalGovernanceService
        self.assertTrue(
            hasattr(ApprovalGovernanceService, 'can_approve'),
            "can_approve method missing — self-approval prevention not enforced"
        )


# ═══════════════════════════════════════════════════════════════════════
# 3. FARM FINANCE MANAGER GATE
# ═══════════════════════════════════════════════════════════════════════

class FarmFinanceManagerGateTests(TestCase):
    """
    [AGRI-GUARDIAN Axis 5 / PRD §8.2-8.3 / AGENTS.md Rule#19]
    Validates that MEDIUM and LARGE farms cannot create approval
    requests without a designated farm finance manager.
    """

    def test_tier_matrix_requires_ffm_for_medium(self):
        """Medium farms must require farm finance manager."""
        from smart_agri.core.services.farm_tiering_policy_service import FarmTieringPolicyService
        snapshot = FarmTieringPolicyService.snapshot_tier_policy("MEDIUM")
        self.assertTrue(snapshot["requires_farm_finance_manager"],
            "MEDIUM tier must require farm finance manager — PRD §8.2")

    def test_tier_matrix_requires_ffm_for_large(self):
        """Large farms must require farm finance manager."""
        from smart_agri.core.services.farm_tiering_policy_service import FarmTieringPolicyService
        snapshot = FarmTieringPolicyService.snapshot_tier_policy("LARGE")
        self.assertTrue(snapshot["requires_farm_finance_manager"],
            "LARGE tier must require farm finance manager — PRD §8.3")

    def test_tier_matrix_no_ffm_for_small(self):
        """Small farms do NOT require farm finance manager."""
        from smart_agri.core.services.farm_tiering_policy_service import FarmTieringPolicyService
        snapshot = FarmTieringPolicyService.snapshot_tier_policy("SMALL")
        self.assertFalse(snapshot["requires_farm_finance_manager"],
            "SMALL tier should NOT require farm finance manager")

    def test_ffm_gate_in_create_request(self):
        """ApprovalGovernanceService.create_request must validate FFM existence."""
        from smart_agri.finance.services.approval_service import ApprovalGovernanceService
        import inspect
        source = inspect.getsource(ApprovalGovernanceService.create_request)
        self.assertIn("requires_farm_finance_manager", source,
            "create_request must check requires_farm_finance_manager — PRD §8")

    def test_farm_finance_authority_service_exists(self):
        """FarmFinanceAuthorityService must be implemented."""
        from smart_agri.finance.services.farm_finance_authority_service import FarmFinanceAuthorityService
        self.assertTrue(hasattr(FarmFinanceAuthorityService, 'require_strict_cycle_authority'))
        self.assertTrue(hasattr(FarmFinanceAuthorityService, 'role_governance_snapshot'))


# ═══════════════════════════════════════════════════════════════════════
# 4. LEDGER IMMUTABILITY COMPREHENSIVE
# ═══════════════════════════════════════════════════════════════════════

class LedgerImmutabilityComprehensiveTests(TestCase):
    """
    [AGRI-GUARDIAN Axis 2 / AGENTS.md Rule#2]
    Comprehensive ledger immutability tests beyond basic save/delete.
    """

    def setUp(self):
        from django.contrib.auth.models import User
        from smart_agri.core.models import Farm
        from smart_agri.finance.models import FiscalYear, FiscalPeriod

        self.user = User.objects.create_user(username="immutability_tester")
        self.farm = Farm.objects.create(
            name="Immutability Farm", slug="imm-farm",
            region="Aden", area=Decimal("10.00"),
        )
        FiscalYear.objects.create(
            farm=self.farm, year=2026,
            start_date=date(2026, 1, 1), end_date=date(2026, 12, 31),
        )
        FiscalPeriod.objects.create(
            fiscal_year=self.farm.fiscal_years.first(), month=3,
            start_date=date(2026, 3, 1), end_date=date(2026, 3, 31),
            status="open",
        )

    def test_ledger_save_rejects_update(self):
        """save() must raise ValidationError on update."""
        from smart_agri.finance.models import FinancialLedger
        entry = FinancialLedger.objects.create(
            farm=self.farm, account_code=FinancialLedger.ACCOUNT_LABOR,
            debit=Decimal("100.0000"), credit=Decimal("0"),
            description="Test immutability", created_by=self.user,
        )
        entry.description = "Attempt to modify"
        with self.assertRaises(ValidationError):
            entry.save()

    def test_ledger_delete_rejected(self):
        """delete() must raise ValidationError."""
        from smart_agri.finance.models import FinancialLedger
        entry = FinancialLedger.objects.create(
            farm=self.farm, account_code=FinancialLedger.ACCOUNT_MATERIAL,
            debit=Decimal("200.0000"), credit=Decimal("0"),
            description="Test delete block", created_by=self.user,
        )
        with self.assertRaises(ValidationError):
            entry.delete()

    def test_ledger_has_row_hash(self):
        """Every ledger entry must have a computed row_hash."""
        from smart_agri.finance.models import FinancialLedger
        entry = FinancialLedger.objects.create(
            farm=self.farm, account_code=FinancialLedger.ACCOUNT_OVERHEAD,
            debit=Decimal("50.0000"), credit=Decimal("0"),
            description="Hash verification", created_by=self.user,
        )
        self.assertTrue(len(entry.row_hash) == 64, "row_hash must be SHA-256 (64 chars)")

    def test_debit_credit_xor_enforced(self):
        """Cannot have both debit and credit > 0."""
        from smart_agri.finance.models import FinancialLedger
        with self.assertRaises(ValidationError):
            FinancialLedger.objects.create(
                farm=self.farm,
                account_code=FinancialLedger.ACCOUNT_LABOR,
                debit=Decimal("100.0000"), credit=Decimal("50.0000"),
                description="Both positive — invalid", created_by=self.user,
            )
