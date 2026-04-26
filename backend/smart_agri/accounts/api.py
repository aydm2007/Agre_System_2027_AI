"""
[AGRI-GUARDIAN] Accounts API — Router Hub
═════════════════════════════════════════

This module is the single entry-point for all Accounts API viewsets.
All viewsets are imported from domain-specific sub-modules:

    api_membership.py   → FarmMembershipViewSet
    api_governance.py   → FarmGovernanceProfileViewSet, RaciTemplateViewSet, RoleDelegationViewSet
    api_auth.py         → UserViewSet, GroupViewSet, PermissionViewSet

URL routing is preserved: ``from smart_agri.accounts.api import router``
"""
from rest_framework import routers

# ─── Domain Imports ──────────────────────────────────────────────────────────

from smart_agri.accounts.api_membership import (
    FarmMembershipViewSet,
    FarmMembershipSerializer,
)

from smart_agri.accounts.api_governance import (
    FarmGovernanceProfileViewSet,
    FarmGovernanceProfileSerializer,
    RaciTemplateViewSet,
    RaciTemplateSerializer,
    RoleDelegationViewSet,
    RoleDelegationSerializer,
    PermissionTemplateViewSet,
    PermissionTemplateSerializer,
)

from smart_agri.accounts.api_auth import (
    UserViewSet,
    UserSerializer,
    GroupViewSet,
    GroupSerializer,
    PermissionViewSet,
    SimplePermissionSerializer,
)

# ─── Router Registration ────────────────────────────────────────────────────

router = routers.DefaultRouter()
router.register(r"memberships", FarmMembershipViewSet, basename="memberships")
router.register(r"governance/farm-profiles", FarmGovernanceProfileViewSet, basename="governance-farm-profiles")
router.register(r"governance/raci-templates", RaciTemplateViewSet, basename="governance-raci-templates")
router.register(r"governance/role-delegations", RoleDelegationViewSet, basename="governance-role-delegations")
router.register(r"auth/users", UserViewSet, basename="auth-users")
router.register(r"auth/groups", GroupViewSet, basename="auth-groups")
router.register(r"auth/permissions", PermissionViewSet, basename="auth-permissions")
router.register(r"governance/permission-templates", PermissionTemplateViewSet, basename="governance-permission-templates")
