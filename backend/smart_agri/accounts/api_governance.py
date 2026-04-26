"""
[AGRI-GUARDIAN] Accounts API - Governance & RACI
Extracted from accounts/api.py for maintainability.
"""
from django.utils import timezone
from rest_framework import permissions, serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from smart_agri.core.api.viewsets.base import AuditedModelViewSet
from smart_agri.accounts.models import (
    FarmMembership, FarmGovernanceProfile, RaciTemplate,
    RoleDelegation, PermissionTemplate,
)

from smart_agri.accounts.permissions_utils import (
    MANAGER_ROLES,
    _user_farm_ids,
    _require_permission,
)
from smart_agri.accounts.services import GovernanceService


def _user_can_manage_farm_scope(user, farm_id=None):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    if farm_id is None:
        return False
    membership = FarmMembership.objects.filter(user=user, farm_id=farm_id).first()
    return bool(membership and membership.role in MANAGER_ROLES)


def _profile_capabilities(*, user):
    can_manage = bool(
        user
        and getattr(user, "is_authenticated", False)
        and (
            getattr(user, "is_superuser", False)
            or user.has_perm("accounts.add_farmgovernanceprofile")
            or user.has_perm("accounts.change_farmgovernanceprofile")
        )
    )
    return {
        "can_manage": can_manage,
        "can_create": can_manage,
        "can_update": can_manage,
    }


def _delegation_capabilities(*, user, farm_id):
    can_scope_manage = _user_can_manage_farm_scope(user, farm_id=farm_id)
    can_create = can_scope_manage
    can_update = can_scope_manage and (getattr(user, "is_superuser", False) or user.has_perm("accounts.change_roledelegation"))
    can_delete = can_scope_manage and (getattr(user, "is_superuser", False) or user.has_perm("accounts.delete_roledelegation"))
    return {
        "can_manage": can_scope_manage,
        "can_create": can_create,
        "can_update": can_update,
        "can_delete": can_delete,
    }


# ─── Serializers ─────────────────────────────────────────────────────────────

class FarmGovernanceProfileSerializer(serializers.ModelSerializer):
    farm_name = serializers.CharField(source="farm.name", read_only=True)
    suggested_tier = serializers.SerializerMethodField()
    capabilities = serializers.SerializerMethodField()

    class Meta:
        model = FarmGovernanceProfile
        fields = [
            "id",
            "farm",
            "farm_name",
            "tier",
            "suggested_tier",
            "capabilities",
            "rationale",
            "approved_by",
            "approved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "approved_at"]

    def get_suggested_tier(self, obj):
        area = getattr(obj.farm, "area", None)
        if area is None:
            return FarmGovernanceProfile.TIER_MEDIUM
        if area < 50:
            return FarmGovernanceProfile.TIER_SMALL
        if area < 250:
            return FarmGovernanceProfile.TIER_MEDIUM
        return FarmGovernanceProfile.TIER_LARGE

    def get_capabilities(self, obj):
        request = self.context.get("request")
        return _profile_capabilities(user=getattr(request, "user", None))


class RaciTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RaciTemplate
        fields = [
            "id",
            "name",
            "tier",
            "version",
            "matrix",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class RoleDelegationSerializer(serializers.ModelSerializer):
    principal_username = serializers.CharField(source="principal_user.username", read_only=True)
    delegate_username = serializers.CharField(source="delegate_user.username", read_only=True)
    farm_name = serializers.CharField(source="farm.name", read_only=True)
    is_currently_effective = serializers.BooleanField(read_only=True)
    capabilities = serializers.SerializerMethodField()

    class Meta:
        model = RoleDelegation
        fields = [
            "id",
            "farm",
            "farm_name",
            "principal_user",
            "principal_username",
            "delegate_user",
            "delegate_username",
            "role",
            "reason",
            "starts_at",
            "ends_at",
            "is_active",
            "is_currently_effective",
            "capabilities",
            "approved_by",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_by", "created_at", "updated_at", "is_currently_effective"]

    def validate(self, attrs):
        starts_at = attrs.get("starts_at")
        ends_at = attrs.get("ends_at")
        if starts_at and ends_at and ends_at <= starts_at:
            raise ValidationError({"ends_at": "must be later than starts_at"})
        return attrs

    def get_capabilities(self, obj):
        request = self.context.get("request")
        return _delegation_capabilities(user=getattr(request, "user", None), farm_id=obj.farm_id)


# ─── ViewSets ────────────────────────────────────────────────────────────────

class FarmGovernanceProfileViewSet(AuditedModelViewSet):
    serializer_class = FarmGovernanceProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = FarmGovernanceProfile.objects.select_related("farm", "approved_by")

    def get_queryset(self):
        qs = super().get_queryset()
        farm_param = self.request.query_params.get("farm") or self.request.query_params.get("farm_id")
        if farm_param:
            qs = qs.filter(farm_id=farm_param)
        if self.request.user.is_superuser:
            return qs.order_by("farm__name")
        farm_ids = _user_farm_ids(self.request.user)
        return qs.filter(farm_id__in=farm_ids).order_by("farm__name")

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        data = response.data
        meta = dict(data.get("meta", {})) if isinstance(data, dict) else {}
        meta.update(_profile_capabilities(user=request.user))
        if isinstance(data, list):
            response.data = {"results": data, "meta": meta}
        else:
            data["meta"] = meta
        return response

    def perform_create(self, serializer):
        GovernanceService.create_farm_governance_profile(serializer=serializer, actor=self.request.user)

    def perform_update(self, serializer):
        GovernanceService.update_farm_governance_profile(serializer=serializer, actor=self.request.user)


class RaciTemplateViewSet(AuditedModelViewSet):
    serializer_class = RaciTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = RaciTemplate.objects.all().order_by("tier", "name")

    def get_queryset(self):
        qs = super().get_queryset()
        tier = self.request.query_params.get("tier")
        if tier:
            qs = qs.filter(tier=tier)
        return qs

    def perform_create(self, serializer):
        GovernanceService.create_raci_template(serializer=serializer, actor=self.request.user)

    def perform_update(self, serializer):
        GovernanceService.update_raci_template(serializer=serializer, actor=self.request.user)

    @action(detail=False, methods=["post"], url_path="seed-defaults")
    def seed_defaults(self, request):
        result = GovernanceService.seed_default_raci_templates(actor=request.user)
        return Response(result)


class RoleDelegationViewSet(AuditedModelViewSet):
    serializer_class = RoleDelegationSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = RoleDelegation.objects.select_related("farm", "principal_user", "delegate_user")

    def get_queryset(self):
        qs = super().get_queryset()
        farm_param = self.request.query_params.get("farm") or self.request.query_params.get("farm_id")
        if farm_param:
            qs = qs.filter(farm_id=farm_param)
        if self.request.user.is_superuser:
            return qs.order_by("-created_at")
        farm_ids = _user_farm_ids(self.request.user)
        return qs.filter(farm_id__in=farm_ids).order_by("-created_at")

    def perform_create(self, serializer):
        GovernanceService.create_role_delegation(serializer=serializer, actor=self.request.user)

    def _user_can_manage_farm(self, farm_id):
        return _user_can_manage_farm_scope(self.request.user, farm_id=farm_id)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        farm_param = request.query_params.get("farm") or request.query_params.get("farm_id")
        try:
            farm_id = int(farm_param) if farm_param is not None else None
        except (TypeError, ValueError):
            farm_id = None
        data = response.data
        meta = dict(data.get("meta", {})) if isinstance(data, dict) else {}
        meta.update(_delegation_capabilities(user=request.user, farm_id=farm_id))
        if isinstance(data, list):
            response.data = {"results": data, "meta": meta}
        else:
            data["meta"] = meta
        return response

    def perform_update(self, serializer):
        GovernanceService.update_role_delegation(serializer=serializer, actor=self.request.user)

    def perform_destroy(self, instance):
        GovernanceService.delete_role_delegation(instance=instance, actor=self.request.user)


# ─── Permission Templates ────────────────────────────────────────────────────

class PermissionTemplateSerializer(serializers.ModelSerializer):
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = PermissionTemplate
        fields = [
            "id", "name", "slug", "description",
            "is_system", "user_count",
            "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "user_count"]

    def get_user_count(self, obj):
        return obj.users.count()


class PermissionTemplateViewSet(AuditedModelViewSet):
    """
    [AGRI-GUARDIAN] CRUD for PermissionTemplate.
    Restricted to superusers and system administrators.
    """
    serializer_class = PermissionTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = PermissionTemplate.objects.all().order_by("name")

    def get_queryset(self):
        user = self.request.user
        if not user.is_superuser and not user.is_staff:
            raise PermissionDenied("إدارة القوالب مقصورة على مدير النظام.")
        return super().get_queryset()

    def perform_create(self, serializer):
        GovernanceService.create_permission_template(serializer=serializer, actor=self.request.user)

    def perform_update(self, serializer):
        GovernanceService.update_permission_template(serializer=serializer, actor=self.request.user)

    def perform_destroy(self, instance):
        GovernanceService.delete_permission_template(instance=instance, actor=self.request.user)
