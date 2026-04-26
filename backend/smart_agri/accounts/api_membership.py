"""
[AGRI-GUARDIAN] Accounts API - Farm Membership
Extracted from accounts/api.py for maintainability.
"""
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import permissions, serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from smart_agri.core.api.viewsets.base import AuditedModelViewSet
from smart_agri.core.models import Farm
from smart_agri.accounts.models import FarmMembership
from smart_agri.accounts.permissions_utils import (
    MANAGER_ROLES,
    _user_farm_ids,
)
from smart_agri.accounts.services import MembershipService


# ─── Serializers ─────────────────────────────────────────────────────────────

class FarmMembershipSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    full_name = serializers.SerializerMethodField()
    email = serializers.EmailField(source="user.email", read_only=True)
    farm_name = serializers.CharField(source="farm.name", read_only=True)
    user_id = serializers.IntegerField(read_only=True)
    farm_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = FarmMembership
        fields = [
            "id",
            "user",
            "farm",
            "role",
            "username",
            "full_name",
            "email",
            "farm_name",
            "user_id",
            "farm_id",
        ]
        extra_kwargs = {
            "user": {"write_only": True},
            "farm": {"write_only": True},
        }

    def get_full_name(self, obj):
        user = getattr(obj, 'user', None)
        if user is None and isinstance(obj, dict):
            user = obj.get('user')
        if not user:
            return ''
        full_name = user.get_full_name() if hasattr(user, 'get_full_name') else ''
        return full_name or getattr(user, 'username', '')



# ─── ViewSets ────────────────────────────────────────────────────────────────

class FarmMembershipViewSet(AuditedModelViewSet):
    serializer_class = FarmMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = FarmMembership.objects.select_related("user", "farm")

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if not user.is_superuser:
            farm_ids = _user_farm_ids(user)
            qs = qs.filter(farm_id__in=farm_ids)
        farm_param = self.request.query_params.get("farm") or self.request.query_params.get("farm_id")
        if farm_param:
            qs = qs.filter(farm_id=farm_param)
        return qs.order_by("farm__name", "user__username")

    def _user_can_manage_farm(self, farm):
        user = self.request.user
        if user.is_superuser:
            return True
        if not user.is_authenticated or farm is None:
            return False
        if isinstance(farm, int):
            membership = FarmMembership.objects.filter(user=user, farm_id=farm).first()
        else:
            membership = FarmMembership.objects.filter(user=user, farm=farm).first()
        return bool(membership and membership.role in MANAGER_ROLES)

    def _ensure_can_manage(self, farm):
        MembershipService.ensure_manage_farm(self.request.user, farm)

    def _ensure_admin_remains(self, farm, exclude_membership_id=None):
        MembershipService.ensure_admin_remains(farm, exclude_membership_id=exclude_membership_id)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        farm_param = request.query_params.get("farm") or request.query_params.get("farm_id")
        try:
            farm_id = int(farm_param) if farm_param is not None else None
        except (TypeError, ValueError):
            farm_id = None
        can_manage = self._user_can_manage_farm(farm_id)
        data = response.data
        if isinstance(data, list):
            response.data = {"results": data, "meta": {"can_manage": can_manage}}
        else:
            meta = dict(data.get("meta", {}))
            meta["can_manage"] = can_manage
            data["meta"] = meta
        return response

    def perform_create(self, serializer):
        MembershipService.create_membership(serializer=serializer, actor=self.request.user)

    def perform_update(self, serializer):
        MembershipService.update_membership(serializer=serializer, actor=self.request.user)

    def perform_destroy(self, instance):
        MembershipService.delete_membership(instance=instance, actor=self.request.user)

    @action(detail=False, methods=["get"], url_path="roles")
    def roles(self, request):
        roles = [
            {"value": value, "label": label}
            for value, label in FarmMembership.ROLE_CHOICES
        ]
        return Response({"results": roles})

    @action(detail=False, methods=["get"], url_path="available-users")
    def available_users(self, request):
        farm_id = request.query_params.get("farm") or request.query_params.get("farm_id")
        if not farm_id:
            raise ValidationError({"farm": "يجب تحديد المزرعة."})
        farm = get_object_or_404(Farm, pk=farm_id)
        self._ensure_can_manage(farm)

        query = request.query_params.get("q", "").strip()
        qs = User.objects.filter(is_active=True).exclude(farm_memberships__farm=farm)
        if query:
            qs = qs.filter(
                Q(username__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(email__icontains=query)
            )
        qs = qs.order_by("username")[:25]
        data = [
            {
                "id": u.id,
                "username": u.username,
                "full_name": u.get_full_name() or u.username,
                "email": u.email,
            }
            for u in qs
        ]
        return Response({"results": data})
