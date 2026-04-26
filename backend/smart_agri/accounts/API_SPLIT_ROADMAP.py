"""
[AGRI-GUARDIAN] Accounts API Split Roadmap
==========================================

This module documents the planned extraction of accounts/api.py (967 lines)
into domain-specific viewset modules.

Current structure (api.py):
    Lines 1-24       : Imports
    Lines 25-140     : Permission utilities
    Lines 143-270    : Auth Serializers (Group, Permission, User, FarmMembership)
    Lines 273-430    : UserViewSet
    Lines 433-560    : GroupViewSet
    Lines 563-630    : PermissionViewSet
    Lines 633-700    : FarmMembershipViewSet
    Lines 703-780    : FarmGovernanceProfileViewSet
    Lines 783-874    : RaciTemplateViewSet
    Lines 877-956    : RoleDelegationViewSet
    Lines 957-967    : Router registrations

Planned extraction order (lowest risk first):
    1. Permission utilities → permissions_utils.py
    2. Governance viewsets → api_governance.py (FarmGovernanceProfile, RACI, RoleDelegation)
    3. Auth viewsets → api_auth.py (User, Group, Permission)
    4. Membership viewsets → api_membership.py

After extraction, api.py becomes a 40-line router-only file that imports
and registers each viewset from sub-modules.

Status: DEFERRED (no-regression mode active; these files are production-critical)
"""
