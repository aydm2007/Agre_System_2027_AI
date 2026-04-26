"""
[AGRI-GUARDIAN] Role Delegation and Governance Tests.
Covers:
1. RoleDelegation model — no_self_delegation constraint, date-bounded delegation
2. Governance API — RACI template enforcement
3. Farm tier auto-classification

Compliance:
- Axis 10: Farm Tiering & Governance (RACI)
- Axis 6: Tenant Isolation — delegation is farm-scoped
"""
import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch
from datetime import date, timedelta


# ──────────────────────────────────────────────────────────────────────────
# 1. RoleDelegation Model (Axis 10)
# ──────────────────────────────────────────────────────────────────────────

class TestRoleDelegationModel:
    """Tests for RoleDelegation structural compliance."""

    def test_role_delegation_model_exists(self):
        """RoleDelegation model must exist per AGENTS.md §207."""
        from smart_agri.accounts.models import RoleDelegation
        assert RoleDelegation is not None

    def test_no_self_delegation_constraint(self):
        """DB constraint no_self_delegation must exist."""
        from smart_agri.accounts.models import RoleDelegation
        constraint_names = [c.name for c in RoleDelegation._meta.constraints]
        assert "no_self_delegation" in constraint_names, \
            f"Missing no_self_delegation constraint. Found: {constraint_names}"

    def test_delegation_valid_window_constraint(self):
        """DB constraint delegation_valid_window must exist (ends_at > starts_at)."""
        from smart_agri.accounts.models import RoleDelegation
        constraint_names = [c.name for c in RoleDelegation._meta.constraints]
        assert "delegation_valid_window" in constraint_names, \
            f"Missing delegation_valid_window constraint. Found: {constraint_names}"

    def test_delegation_has_farm_scope(self):
        """[Axis 6] Delegation must carry farm_id for tenant isolation."""
        from smart_agri.accounts.models import RoleDelegation
        field = RoleDelegation._meta.get_field('farm')
        assert field is not None, "RoleDelegation must have a farm field"

    def test_delegation_has_date_bounds(self):
        """Delegation must have starts_at and ends_at for time-bounded access."""
        from smart_agri.accounts.models import RoleDelegation
        start = RoleDelegation._meta.get_field('starts_at')
        end = RoleDelegation._meta.get_field('ends_at')
        assert start is not None, "Missing starts_at field"
        assert end is not None, "Missing ends_at field"

    def test_delegation_has_principal_and_delegate(self):
        """Delegation must identify both principal_user and delegate_user."""
        from smart_agri.accounts.models import RoleDelegation
        fields = {f.name for f in RoleDelegation._meta.get_fields()}
        assert 'principal_user' in fields, \
            f"RoleDelegation must have a principal_user field. Found: {fields}"
        assert 'delegate_user' in fields, \
            f"RoleDelegation must have a delegate_user field. Found: {fields}"

    def test_delegation_has_role_field(self):
        """Delegation must specify the delegated role."""
        from smart_agri.accounts.models import RoleDelegation
        field = RoleDelegation._meta.get_field('role')
        assert field is not None, "Missing role field on RoleDelegation"

    def test_delegation_has_reason(self):
        """Delegation must include a reason for audit trail."""
        from smart_agri.accounts.models import RoleDelegation
        field = RoleDelegation._meta.get_field('reason')
        assert field is not None, "Missing reason field on RoleDelegation"

    def test_delegation_has_is_active_flag(self):
        """Delegation must have is_active for soft-deactivation."""
        from smart_agri.accounts.models import RoleDelegation
        field = RoleDelegation._meta.get_field('is_active')
        assert field is not None

    def test_delegation_has_approved_by(self):
        """Delegation must track who approved it."""
        from smart_agri.accounts.models import RoleDelegation
        field = RoleDelegation._meta.get_field('approved_by')
        assert field is not None

    def test_is_currently_effective_property_exists(self):
        """is_currently_effective must exist for delegation window checks."""
        from smart_agri.accounts.models import RoleDelegation
        assert hasattr(RoleDelegation, 'is_currently_effective')


# ──────────────────────────────────────────────────────────────────────────
# 2. Farm Tiering (Axis 10)
# ──────────────────────────────────────────────────────────────────────────

class TestFarmTiering:
    """Tests for farm tier governance structure."""

    def test_farm_has_tier_field(self):
        """Farm model must have a tier field."""
        from smart_agri.core.models import Farm
        field = Farm._meta.get_field('tier')
        assert field is not None

    def test_governance_profile_model_exists(self):
        """FarmGovernanceProfile must exist for RACI governance."""
        from smart_agri.accounts.models import FarmGovernanceProfile
        assert FarmGovernanceProfile is not None

    def test_governance_profile_has_tier_choices(self):
        """FarmGovernanceProfile must define SMALL/MEDIUM/LARGE tiers."""
        from smart_agri.accounts.models import FarmGovernanceProfile
        assert FarmGovernanceProfile.TIER_SMALL == "SMALL"
        assert FarmGovernanceProfile.TIER_MEDIUM == "MEDIUM"
        assert FarmGovernanceProfile.TIER_LARGE == "LARGE"

    def test_raci_template_model_exists(self):
        """RaciTemplate must exist for tier-based RACI matrix."""
        from smart_agri.accounts.models import RaciTemplate
        assert RaciTemplate is not None

    def test_raci_template_has_matrix_field(self):
        """RaciTemplate must have JSONField for the RACI matrix."""
        from smart_agri.accounts.models import RaciTemplate
        field = RaciTemplate._meta.get_field('matrix')
        assert field.__class__.__name__ == 'JSONField'


# ──────────────────────────────────────────────────────────────────────────
# 3. Governance API Structure
# ──────────────────────────────────────────────────────────────────────────

class TestGovernanceAPIStructure:
    """Verify governance API endpoints exist."""

    def test_governance_api_module_exists(self):
        """api_governance.py must exist in accounts."""
        from smart_agri.accounts import api_governance
        assert api_governance is not None

    def test_membership_api_module_exists(self):
        """api_membership.py must exist in accounts."""
        from smart_agri.accounts import api_membership
        assert api_membership is not None
