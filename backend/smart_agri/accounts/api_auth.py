"""
[AGRI-GUARDIAN] Auth API - Users, Groups, Permissions
Extracted from accounts/api.py for maintainability.
"""
from django.contrib.auth.models import Group, Permission, User
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from smart_agri.core.api.viewsets.base import AuditedModelViewSet
from smart_agri.core.strict_mode_permissions import is_strict_permission
from smart_agri.accounts.models import FarmMembership
from smart_agri.accounts.services import GroupWriteService, UserWriteService
from smart_agri.accounts.permissions_utils import (
    _with_permission_arabic,
    _user_is_farm_manager,
    _user_farm_ids,
    _user_farm_roles,
    _user_has_admin_role,
    _require_permission,
    _log_strict_permission_grant,
)


# ─── Serializers ─────────────────────────────────────────────────────────────

class SimpleGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name"]


class SimplePermissionSerializer(serializers.ModelSerializer):
    content_type = serializers.SerializerMethodField()
    name_arabic = serializers.SerializerMethodField()
    is_strict = serializers.SerializerMethodField()

    class Meta:
        model = Permission
        fields = ["id", "name", "name_arabic", "codename", "content_type", "is_strict"]

    def get_name_arabic(self, obj):
        return getattr(obj, 'name_arabic', None) or getattr(obj, 'name_arabic_value', None)

    def get_content_type(self, obj):
        return {
            'id': obj.content_type_id,
            'app_label': obj.content_type.app_label,
            'model': obj.content_type.model,
        }

    def get_is_strict(self, obj):
        """[AGRI-GUARDIAN Axis 6] Tag permissions belonging to strict-mode interfaces."""
        return is_strict_permission(obj.codename)


class UserSerializer(serializers.ModelSerializer):
    groups = SimpleGroupSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "is_superuser",
            "last_login",
            "date_joined",
            "password",
            "groups",
        ]
        read_only_fields = ["last_login", "date_joined"]
        extra_kwargs = {"password": {"write_only": True, "required": False}}

    def create(self, validated_data):
        actor = self.context["request"].user
        return UserWriteService.create_user(actor=actor, **validated_data)

    def update(self, instance, validated_data):
        actor = self.context["request"].user
        return UserWriteService.update_user(actor=actor, instance=instance, **validated_data)


class GroupSerializer(serializers.ModelSerializer):
    permissions = serializers.PrimaryKeyRelatedField(
        queryset=Permission.objects.all(), many=True, required=False
    )

    class Meta:
        model = Group
        fields = ["id", "name", "permissions"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["permissions"] = [perm.id for perm in instance.permissions.all()]
        return data


# ─── ViewSets ────────────────────────────────────────────────────────────────

class UserViewSet(AuditedModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = User.objects.all().order_by("username")

    def _ensure_can_manage_superuser(self, request):
        if request.user.is_superuser:
            return
        if _user_has_admin_role(request.user):
            return
        raise PermissionDenied("لا تملك صلاحية إدارة المستخدمين.")

    def _check_superuser_mutation(self, request):
        if "is_superuser" not in request.data:
            return
        self._ensure_can_manage_superuser(request)

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if user.is_superuser:
            return qs
        roles = _user_farm_roles(user)
        if "مدير النظام" in roles:
            return qs
        if "مدير المزرعة" in roles or "مشرف ميداني" in roles:
            farm_ids = _user_farm_ids(user)
            if not farm_ids:
                return qs.none()
            return qs.filter(farm_memberships__farm_id__in=farm_ids).distinct()
        if user.has_perm("auth.view_user"):
            return qs
        return qs.filter(id=user.id)

    def list(self, request, *args, **kwargs):
        _require_permission(request.user, "auth.view_user")
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.id != request.user.id:
            _require_permission(request.user, "auth.view_user")
        serializer = self.get_serializer(instance)
        data = serializer.data
        data["permissions"] = [
            perm.id for perm in instance.user_permissions.all()
        ]
        return Response(data)

    def create(self, request, *args, **kwargs):
        _require_permission(request.user, "auth.add_user")
        self._check_superuser_mutation(request)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        _require_permission(request.user, "auth.change_user")
        self._check_superuser_mutation(request)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        _require_permission(request.user, "auth.change_user")
        self._check_superuser_mutation(request)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        _require_permission(request.user, "auth.delete_user")
        return super().destroy(request, *args, **kwargs)

    def perform_destroy(self, instance):
        UserWriteService.delete_user(actor=self.request.user, instance=instance)

    @action(detail=True, methods=["get", "post"], url_path="permissions")
    def manage_permissions(self, request, pk=None):
        user = self.get_object()

        if request.method.lower() == "get":
            perms_qs = _with_permission_arabic(
                user.user_permissions.all().order_by("codename")
            )
            perms = [
                {
                    "id": perm.id,
                    "name": perm.name,
                    "name_arabic": getattr(perm, "name_arabic", None)
                    or getattr(perm, "name_arabic_value", None),
                    "codename": perm.codename,
                    "is_strict": is_strict_permission(perm.codename),
                }
                for perm in perms_qs
            ]
            return Response({"permissions": perms})

        _require_permission(request.user, "auth.change_user")
        permission_id = request.data.get("permission_id")
        confirmed = request.data.get("confirmed", False)
        if not permission_id:
            raise ValidationError({"permission_id": "معرّف الصلاحية غير صالح."})
        try:
            permission = Permission.objects.get(pk=permission_id)
        except (Permission.DoesNotExist, ValueError, TypeError):
            raise ValidationError({"permission_id": "معرّف الصلاحية غير صالح."})

        # [AGRI-GUARDIAN Axis 6 / AGENTS.md L30] Strict-mode permission warning
        if is_strict_permission(permission.codename):
            from smart_agri.core.models.settings import SystemSettings
            settings = SystemSettings.load()
            if not settings.strict_erp_mode and not confirmed:
                return Response(
                    {
                        "strict_mode_warning": True,
                        "permission_codename": permission.codename,
                        "permission_name": permission.name,
                        "message": (
                            "هذه الصلاحية تتبع المود الصارم (الإدارة المالية). "
                            "النظام حالياً في المود البسيط — هل تريد المتابعة؟"
                        ),
                    },
                    status=status.HTTP_200_OK,
                )
            # Log audit when confirmed in simple mode
            if not settings.strict_erp_mode and confirmed:
                _log_strict_permission_grant(
                    actor=request.user,
                    target_user=user,
                    permission=permission,
                    action_type="GRANT",
                )

        UserWriteService.add_user_permission(actor=request.user, user=user, permission=permission)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["delete"], url_path="permissions/(?P<permission_id>[^/.]+)")
    def remove_permission(self, request, pk=None, permission_id=None):
        _require_permission(request.user, "auth.change_user")
        user = self.get_object()
        permission = get_object_or_404(Permission, pk=permission_id)
        UserWriteService.remove_user_permission(actor=request.user, user=user, permission=permission)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get", "post"], url_path="groups")
    def manage_groups(self, request, pk=None):
        user = self.get_object()

        if request.method.lower() == "get":
            groups_qs = user.groups.all().order_by("name")
            groups = []
            for group in groups_qs:
                strict_perms = [
                    p.codename
                    for p in group.permissions.all()
                    if is_strict_permission(p.codename)
                ]
                groups.append({
                    "id": group.id,
                    "name": group.name,
                    "has_strict_permissions": len(strict_perms) > 0,
                    "strict_permission_count": len(strict_perms),
                })
            return Response({"groups": groups})

        _require_permission(request.user, "auth.change_user")
        group_id = request.data.get("group_id")
        confirmed = request.data.get("confirmed", False)
        if not group_id:
            raise ValidationError({"group_id": "معرّف المجموعة غير صالح."})
        try:
            group = Group.objects.get(pk=group_id)
        except (Group.DoesNotExist, ValueError, TypeError):
            raise ValidationError({"group_id": "معرّف المجموعة غير صالح."})

        # [AGRI-GUARDIAN Axis 6] Warn if group contains strict-mode permissions
        strict_perms_in_group = [
            p.codename
            for p in group.permissions.all()
            if is_strict_permission(p.codename)
        ]
        if strict_perms_in_group:
            from smart_agri.core.models.settings import SystemSettings
            settings = SystemSettings.load()
            if not settings.strict_erp_mode and not confirmed:
                return Response(
                    {
                        "strict_mode_warning": True,
                        "group_name": group.name,
                        "strict_permissions": strict_perms_in_group,
                        "message": (
                            f"المجموعة '{group.name}' تحتوي على "
                            f"{len(strict_perms_in_group)} صلاحية تتبع المود الصارم. "
                            "النظام حالياً في المود البسيط — هل تريد المتابعة؟"
                        ),
                    },
                    status=status.HTTP_200_OK,
                )
            if not settings.strict_erp_mode and confirmed:
                _log_strict_permission_grant(
                    actor=request.user,
                    target_user=user,
                    permission=None,
                    action_type="GROUP_GRANT",
                    extra={"group": group.name, "strict_perms": strict_perms_in_group},
                )

        UserWriteService.add_user_group(actor=request.user, user=user, group=group)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["delete"], url_path="groups/(?P<group_id>[^/.]+)")
    def remove_from_group(self, request, pk=None, group_id=None):
        _require_permission(request.user, "auth.change_user")
        user = self.get_object()
        group = get_object_or_404(Group, pk=group_id)
        UserWriteService.remove_user_group(actor=request.user, user=user, group=group)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="me", permission_classes=[IsAuthenticated])
    def current_user(self, request):
        user = request.user
        serializer = self.get_serializer(user)
        memberships = (
            FarmMembership.objects.filter(user=user)
            .select_related("farm")
            .order_by("farm__name")
        )
        farms = [
            {
                "membership_id": membership.id,
                "farm_id": membership.farm_id,
                "farm_name": membership.farm.name,
                "role": membership.role,
            }
            for membership in memberships
        ]
        direct_permissions_qs = _with_permission_arabic(user.user_permissions.all())
        group_permissions_qs = _with_permission_arabic(
            Permission.objects.filter(group__user=user).distinct()
        )
        direct_permissions = list(direct_permissions_qs)
        group_permissions = list(group_permissions_qs)
        combined_permissions = sorted(
            {perm.codename for perm in direct_permissions + group_permissions}
        )
        return Response(
            {
                "user": serializer.data,
                "farms": farms,
                "farm_ids": [membership.farm_id for membership in memberships],
                "permissions": combined_permissions,
                "direct_permissions": [
                    {
                        "id": perm.id,
                        "name": perm.name,
                        "name_arabic": getattr(perm, 'name_arabic', None) or getattr(perm, 'name_arabic_value', None),
                        "codename": perm.codename,
                    }
                    for perm in direct_permissions
                ],
                "groups": [
                    {"id": group.id, "name": group.name}
                    for group in user.groups.all().order_by("name")
                ],
                "is_admin": user.is_staff or _user_is_farm_manager(user),
                "is_superuser": user.is_superuser,
            }
        )


class GroupViewSet(AuditedModelViewSet):
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Group.objects.all().order_by("name")

    def list(self, request, *args, **kwargs):
        _require_permission(request.user, "auth.view_group")
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        _require_permission(request.user, "auth.view_group")
        response = super().retrieve(request, *args, **kwargs)
        return response

    def create(self, request, *args, **kwargs):
        _require_permission(request.user, "auth.add_group")
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        _require_permission(request.user, "auth.change_group")
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        _require_permission(request.user, "auth.change_group")
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        _require_permission(request.user, "auth.delete_group")
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.instance = GroupWriteService.create_group(
            actor=self.request.user,
            **serializer.validated_data,
        )

    def perform_update(self, serializer):
        serializer.instance = GroupWriteService.update_group(
            actor=self.request.user,
            instance=self.get_object(),
            **serializer.validated_data,
        )

    def perform_destroy(self, instance):
        GroupWriteService.delete_group(actor=self.request.user, instance=instance)

    @action(detail=True, methods=["post"], url_path="permissions")
    def add_permission(self, request, pk=None):
        _require_permission(request.user, "auth.change_group")
        group = self.get_object()
        permission_id = request.data.get("permission_id")
        if not permission_id:
            raise ValidationError({"permission_id": "معرّف الصلاحية غير صالح."})
        try:
            permission = Permission.objects.get(pk=permission_id)
        except (Permission.DoesNotExist, ValueError, TypeError):
            raise ValidationError({"permission_id": "معرّف الصلاحية غير صالح."})
        GroupWriteService.add_group_permission(actor=request.user, group=group, permission=permission)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["delete"], url_path="permissions/(?P<permission_id>[^/.]+)")
    def remove_permission(self, request, pk=None, permission_id=None):
        _require_permission(request.user, "auth.change_group")
        group = self.get_object()
        permission = get_object_or_404(Permission, pk=permission_id)
        GroupWriteService.remove_group_permission(actor=request.user, group=group, permission=permission)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """All permissions in a single response (no pagination) for UI classification."""
    serializer_class = SimplePermissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None  # Permissions are finite; UI needs all for strict/general split
    queryset = Permission.objects.select_related("content_type").order_by(
        "content_type__app_label", "codename"
    )

    def get_queryset(self):
        base = super().get_queryset()
        return _with_permission_arabic(base)

    def list(self, request, *args, **kwargs):
        _require_permission(request.user, "auth.view_permission")
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        _require_permission(request.user, "auth.view_permission")
        return super().retrieve(request, *args, **kwargs)
