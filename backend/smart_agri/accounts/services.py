"""
Governed write services for accounts and governance workflows.

These helpers keep API/view layers thin and move write ownership into explicit
service methods so the repository aligns better with the service-layer-only
protocol in AGENTS.md.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.contrib.auth.models import Group, Permission, User
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from smart_agri.accounts.models import (
    FarmGovernanceProfile,
    FarmMembership,
    PermissionTemplate,
    RaciTemplate,
    RoleDelegation,
)
from smart_agri.accounts.permissions_utils import MANAGER_ROLES, SOVEREIGN_ROLES, _require_permission, _user_has_admin_role


@dataclass(frozen=True)
class _PermissionContext:
    user: Any



class UserWriteService:
    """Governed service-layer writes for auth users and permission membership."""

    @staticmethod
    def _ensure_can_manage_superuser(actor) -> None:
        if getattr(actor, "is_superuser", False):
            return
        if _user_has_admin_role(actor):
            return
        raise PermissionDenied("لا تملك صلاحية إدارة المستخدمين الفائقين.")

    @staticmethod
    @transaction.atomic
    def create_user(*, actor, **validated_data) -> User:
        _require_permission(actor, "auth.add_user")
        password = validated_data.pop("password", None)
        if not password:
            raise ValidationError({"password": "كلمة المرور مطلوبة."})
        if validated_data.get("is_superuser"):
            UserWriteService._ensure_can_manage_superuser(actor)
        user = User(**validated_data)
        user.set_password(password)
        user.full_clean(exclude=["last_login", "date_joined"])
        user.save()
        return user

    @staticmethod
    @transaction.atomic
    def update_user(*, actor, instance: User, **validated_data) -> User:
        _require_permission(actor, "auth.change_user")
        password = validated_data.pop("password", None)
        locked = User.objects.select_for_update().get(pk=instance.pk)
        if validated_data.get("is_superuser") or locked.is_superuser:
            UserWriteService._ensure_can_manage_superuser(actor)
        for attr, value in validated_data.items():
            setattr(locked, attr, value)
        if password:
            locked.set_password(password)
        locked.full_clean(exclude=["password", "last_login", "date_joined"])
        locked.save()
        return locked

    @staticmethod
    @transaction.atomic
    def delete_user(*, actor, instance: User) -> None:
        _require_permission(actor, "auth.delete_user")
        locked = User.objects.select_for_update().get(pk=instance.pk)
        if locked.is_superuser:
            UserWriteService._ensure_can_manage_superuser(actor)
        if locked.pk == getattr(actor, "pk", None):
            raise ValidationError("لا يمكن حذف حساب المستخدم الحالي.")
        locked.delete()

    @staticmethod
    @transaction.atomic
    def add_user_permission(*, actor, user: User, permission: Permission) -> None:
        _require_permission(actor, "auth.change_user")
        user = User.objects.select_for_update().get(pk=user.pk)
        user.user_permissions.add(permission)

    @staticmethod
    @transaction.atomic
    def remove_user_permission(*, actor, user: User, permission: Permission) -> None:
        _require_permission(actor, "auth.change_user")
        user = User.objects.select_for_update().get(pk=user.pk)
        user.user_permissions.remove(permission)

    @staticmethod
    @transaction.atomic
    def add_user_group(*, actor, user: User, group: Group) -> None:
        _require_permission(actor, "auth.change_user")
        user = User.objects.select_for_update().get(pk=user.pk)
        user.groups.add(group)

    @staticmethod
    @transaction.atomic
    def remove_user_group(*, actor, user: User, group: Group) -> None:
        _require_permission(actor, "auth.change_user")
        user = User.objects.select_for_update().get(pk=user.pk)
        user.groups.remove(group)


class GroupWriteService:
    """Governed service-layer writes for Django auth groups."""

    @staticmethod
    @transaction.atomic
    def create_group(*, actor, **validated_data) -> Group:
        _require_permission(actor, "auth.add_group")
        permissions = list(validated_data.pop("permissions", []))
        group = Group.objects.create(**validated_data)
        if permissions:
            group.permissions.set(permissions)
        return group

    @staticmethod
    @transaction.atomic
    def update_group(*, actor, instance: Group, **validated_data) -> Group:
        _require_permission(actor, "auth.change_group")
        permissions = validated_data.pop("permissions", None)
        locked = Group.objects.select_for_update().get(pk=instance.pk)
        for attr, value in validated_data.items():
            setattr(locked, attr, value)
        locked.full_clean()
        locked.save()
        if permissions is not None:
            locked.permissions.set(permissions)
        return locked

    @staticmethod
    @transaction.atomic
    def delete_group(*, actor, instance: Group) -> None:
        _require_permission(actor, "auth.delete_group")
        locked = Group.objects.select_for_update().get(pk=instance.pk)
        locked.delete()

    @staticmethod
    @transaction.atomic
    def add_group_permission(*, actor, group: Group, permission: Permission) -> None:
        _require_permission(actor, "auth.change_group")
        group = Group.objects.select_for_update().get(pk=group.pk)
        group.permissions.add(permission)

    @staticmethod
    @transaction.atomic
    def remove_group_permission(*, actor, group: Group, permission: Permission) -> None:
        _require_permission(actor, "auth.change_group")
        group = Group.objects.select_for_update().get(pk=group.pk)
        group.permissions.remove(permission)


class MembershipService:
    @staticmethod
    def ensure_manage_farm(actor, farm) -> None:
        if actor.is_superuser:
            return
        if actor is None or not getattr(actor, 'is_authenticated', False) or farm is None:
            raise PermissionDenied("لا تملك صلاحية الوصول إلى هذه المزرعة.")
        farm_id = farm if isinstance(farm, int) else getattr(farm, 'id', None)
        membership = FarmMembership.objects.filter(user=actor, farm_id=farm_id).first()
        if not membership or membership.role not in MANAGER_ROLES:
            raise PermissionDenied("لا تملك صلاحية الوصول إلى هذه المزرعة.")

    @staticmethod
    def ensure_admin_remains(farm, *, exclude_membership_id=None) -> None:
        qs = FarmMembership.objects.filter(farm=farm, role="مدير المزرعة")
        if exclude_membership_id:
            qs = qs.exclude(id=exclude_membership_id)
        if not qs.exists():
            raise ValidationError("يجب أن يبقى مسؤول واحد على الأقل بدور مدير المزرعة في المزرعة.")

    @staticmethod
    @transaction.atomic
    def create_membership(*, serializer, actor):
        farm = serializer.validated_data.get("farm")
        user = serializer.validated_data.get("user")
        MembershipService.ensure_manage_farm(actor, farm)
        role = serializer.validated_data.get("role")
        if role in SOVEREIGN_ROLES and not actor.is_superuser:
            raise PermissionDenied("لا يمكن تعيين الأدوار السيادية إلا من قبل مدير النظام.")
        if FarmMembership.objects.filter(farm=farm, user=user).exists():
            raise ValidationError("هذا المستخدم مرتبط بالمزرعة بالفعل.")
        return serializer.save()

    @staticmethod
    @transaction.atomic
    def update_membership(*, serializer, actor):
        instance = serializer.instance
        MembershipService.ensure_manage_farm(actor, instance.farm)
        new_role = serializer.validated_data.get("role")
        if new_role and new_role in SOVEREIGN_ROLES and not actor.is_superuser:
            raise PermissionDenied("لا يمكن تعيين الأدوار السيادية إلا من قبل مدير النظام.")
        if new_role and new_role != instance.role and instance.role == "مدير المزرعة":
            MembershipService.ensure_admin_remains(instance.farm, exclude_membership_id=instance.id)
        return serializer.save()

    @staticmethod
    @transaction.atomic
    def delete_membership(*, instance, actor):
        MembershipService.ensure_manage_farm(actor, instance.farm)
        if instance.role == "مدير المزرعة":
            MembershipService.ensure_admin_remains(instance.farm, exclude_membership_id=instance.id)
        instance.delete()


class GovernanceService:
    @staticmethod
    @transaction.atomic
    def create_farm_governance_profile(*, serializer, actor):
        _require_permission(actor, "accounts.add_farmgovernanceprofile")
        return serializer.save()

    @staticmethod
    @transaction.atomic
    def update_farm_governance_profile(*, serializer, actor):
        _require_permission(actor, "accounts.change_farmgovernanceprofile")
        instance = serializer.save()
        if "tier" in serializer.validated_data:
            instance.approved_by = actor
            instance.approved_at = timezone.now()
            instance.save(update_fields=["approved_by", "approved_at", "updated_at"])
        return instance

    @staticmethod
    @transaction.atomic
    def create_raci_template(*, serializer, actor):
        _require_permission(actor, "accounts.add_racitemplate")
        return serializer.save(created_by=actor, updated_by=actor)

    @staticmethod
    @transaction.atomic
    def update_raci_template(*, serializer, actor):
        _require_permission(actor, "accounts.change_racitemplate")
        return serializer.save(updated_by=actor)

    @staticmethod
    @transaction.atomic
    def seed_default_raci_templates(*, actor):
        _require_permission(actor, "accounts.add_racitemplate")
        defaults = [
            (
                "قالب مزرعة صغيرة (افتراضي)",
                FarmGovernanceProfile.TIER_SMALL,
                {
                    "daily_operations": {"R": "مدير المزرعة", "A": "مدير المزرعة", "C": "مشرف ميداني", "I": "رئيس الحسابات"},
                    "finance_close": {"R": "رئيس الحسابات", "A": "رئيس الحسابات", "C": "مدير المزرعة", "I": "محاسب القطاع"},
                    "procurement": {"R": "مدير المزرعة", "A": "مدير المزرعة", "C": "أمين مخزن", "I": "محاسب المزرعة"},
                    "harvesting": {"R": "مدير المزرعة", "A": "مدير المزرعة", "C": "مشرف ميداني", "I": "محاسب المزرعة"},
                    "inventory": {"R": "أمين مخزن", "A": "مدير المزرعة", "C": "أمين مخزن", "I": "رئيس الحسابات"},
                },
            ),
            (
                "قالب مزرعة متوسطة (افتراضي)",
                FarmGovernanceProfile.TIER_MEDIUM,
                {
                    "daily_operations": {"R": "مشرف ميداني", "A": "مدير المزرعة", "C": "فني زراعي", "I": "رئيس الحسابات"},
                    "finance_close": {"R": "رئيس الحسابات", "A": "المدير المالي للمزرعة", "C": "محاسب المزرعة", "I": "محاسب القطاع"},
                    "procurement": {"R": "مدير المزرعة", "A": "المدير المالي للمزرعة", "C": "أمين مخزن", "I": "محاسب المزرعة"},
                    "harvesting": {"R": "المهندس الزراعي", "A": "مدير المزرعة", "C": "مشرف ميداني", "I": "محاسب المزرعة"},
                    "inventory": {"R": "أمين مخزن", "A": "مدير المزرعة", "C": "أمين مخزن", "I": "محاسب القطاع"},
                },
            ),
            (
                "قالب مزرعة كبيرة (افتراضي)",
                FarmGovernanceProfile.TIER_LARGE,
                {
                    "daily_operations": {"R": "مشرف ميداني", "A": "مدير المزرعة", "C": "المهندس الزراعي", "I": "رئيس الحسابات"},
                    "finance_close": {"R": "رئيس الحسابات", "A": "المدير المالي للمزرعة", "C": "محاسب المزرعة", "I": "محاسب القطاع"},
                    "procurement": {"R": "مدير المزرعة", "A": "المدير المالي للمزرعة", "C": "أمين مخزن", "I": "رئيس حسابات القطاع"},
                    "harvesting": {"R": "المهندس الزراعي", "A": "مدير المزرعة", "C": "مشرف ميداني", "I": "رئيس الحسابات"},
                    "inventory": {"R": "أمين مخزن", "A": "مدير المزرعة", "C": "محاسب المزرعة", "I": "محاسب القطاع"},
                },
            ),
        ]
        created = 0
        for name, tier, matrix in defaults:
            _, was_created = RaciTemplate.objects.get_or_create(
                name=name,
                defaults={
                    "tier": tier,
                    "version": "v1",
                    "matrix": matrix,
                    "is_active": True,
                    "created_by": actor,
                    "updated_by": actor,
                },
            )
            if was_created:
                created += 1
        return {"created": created, "total_defaults": len(defaults)}

    @staticmethod
    def ensure_manage_delegation(*, actor, farm_id):
        MembershipService.ensure_manage_farm(actor, farm_id)

    @staticmethod
    @transaction.atomic
    def create_role_delegation(*, serializer, actor):
        farm = serializer.validated_data.get("farm")
        principal_user = serializer.validated_data.get("principal_user")
        role = serializer.validated_data.get("role")
        if not actor.is_superuser:
            GovernanceService.ensure_manage_delegation(actor=actor, farm_id=farm.id)
        if not FarmMembership.objects.filter(user=principal_user, farm=farm, role=role).exists():
            raise ValidationError({"principal_user": "المفوِّض لا يحمل هذا الدور فعلياً في المزرعة."})
        return serializer.save(created_by=actor, approved_by=actor)

    @staticmethod
    @transaction.atomic
    def update_role_delegation(*, serializer, actor):
        instance = serializer.instance
        if not actor.is_superuser:
            GovernanceService.ensure_manage_delegation(actor=actor, farm_id=instance.farm_id)
        _require_permission(actor, "accounts.change_roledelegation")
        return serializer.save()

    @staticmethod
    @transaction.atomic
    def delete_role_delegation(*, instance, actor):
        if not actor.is_superuser:
            GovernanceService.ensure_manage_delegation(actor=actor, farm_id=instance.farm_id)
        _require_permission(actor, "accounts.delete_roledelegation")
        instance.delete()

    @staticmethod
    @transaction.atomic
    def create_permission_template(*, serializer, actor):
        _require_permission(actor, "accounts.add_permissiontemplate")
        return serializer.save(created_by=actor, updated_by=actor)

    @staticmethod
    @transaction.atomic
    def update_permission_template(*, serializer, actor):
        _require_permission(actor, "accounts.change_permissiontemplate")
        return serializer.save(updated_by=actor)

    @staticmethod
    @transaction.atomic
    def delete_permission_template(*, instance, actor):
        if instance.is_system:
            raise PermissionDenied("لا يمكن حذف القوالب النظامية.")
        _require_permission(actor, "accounts.delete_permissiontemplate")
        instance.delete()
