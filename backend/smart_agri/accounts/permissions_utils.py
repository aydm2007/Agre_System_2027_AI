"""
[AGRI-GUARDIAN] Accounts API - Permission Utilities
Extracted from accounts/api.py
"""
import logging
from django.contrib.auth.models import Permission
from django.db import connection, OperationalError, ProgrammingError
from django.db.models.expressions import RawSQL
from rest_framework.exceptions import PermissionDenied

from smart_agri.core.models import Farm
from smart_agri.accounts.models import FarmMembership


MANAGER_ROLES = {"مدير المزرعة", "المدير المالي لقطاع المزارع", "رئيس الحسابات", "مدير النظام"}

# [AGRI-GUARDIAN] Sovereign Roles requiring strict audit and visual warnings
SOVEREIGN_ROLES = {
    "المدير المالي لقطاع المزارع", 
    "رئيس الحسابات", 
    "مدير النظام", 
    "محاسب القطاع", 
    "مراجع القطاع",
    "رئيس حسابات القطاع"
}


def _permission_has_name_arabic_column() -> bool:
    table_name = Permission._meta.db_table
    try:
        with connection.cursor() as cursor:
            descriptions = connection.introspection.get_table_description(cursor, table_name)
    except (ImportError, LookupError, OperationalError, ProgrammingError):
        return False
    return any(col.name == "name_arabic" for col in descriptions)


def _with_permission_arabic(queryset):
    """Attach the optional Arabic label when the database column provides it."""
    if not _permission_has_name_arabic_column():
        return queryset
    table_name = Permission._meta.db_table
    return queryset.annotate(name_arabic_value=RawSQL(f'"{table_name}".name_arabic', []))


def _user_is_farm_manager(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    # Check Django groups first (legacy path)
    if user.groups.filter(name__in=MANAGER_ROLES).exists():
        return True
    # Also check FarmMembership.role (primary source of truth)
    return FarmMembership.objects.filter(
        user=user, role__in=MANAGER_ROLES
    ).exists()


def _user_farm_ids(user):
    if not user.is_authenticated:
        return []
    if user.is_superuser:
        return list(Farm.objects.values_list("id", flat=True))
    return list(
        FarmMembership.objects.filter(user=user).values_list("farm_id", flat=True)
    )


def _user_farm_roles(user):
    if not user.is_authenticated:
        return set()
    return set(
        FarmMembership.objects.filter(user=user).values_list("role", flat=True)
    )


def _user_has_admin_role(user):
    if user.is_superuser:
        return True
    return "مدير المزرعة" in _user_farm_roles(user)


def _require_permission(user, perm_codename: str, fallback_manager: bool = True):
    """Ensure the caller has the requested Django permission."""
    if user.is_superuser:
        return
    if perm_codename and user.has_perm(perm_codename):
        return
    if fallback_manager and _user_is_farm_manager(user):
        return
    raise PermissionDenied("لا تملك صلاحية الوصول إلى هذا المورد.")


_strict_perm_logger = logging.getLogger("smart_agri.permissions.strict")


def _log_strict_permission_grant(actor, target_user, permission=None, action_type="GRANT", extra=None):
    """
    [AGRI-GUARDIAN Axis 7] Log an audit entry when a strict-mode permission
    is granted while the system is in Simple (Shadow) mode.
    """
    payload = {
        "action_type": action_type,
        "target_user_id": target_user.id,
        "target_username": target_user.username,
    }
    if permission:
        payload["permission_codename"] = permission.codename
        payload["permission_name"] = permission.name
    if extra:
        payload.update(extra)

    _strict_perm_logger.warning(
        "Strict-mode permission granted in simple mode: actor=%s target=%s type=%s payload=%s",
        actor.username, target_user.username, action_type, payload,
    )
    # Persist to DB audit log if AuditLog model available
    try:
        from smart_agri.core.models import AuditLog
        AuditLog.objects.create(
            action=f"STRICT_PERMISSION_{action_type}_IN_SIMPLE_MODE",
            object_type="Permission",
            object_id=str(permission.id) if permission else "",
            description=(
                f"منح صلاحية المود الصارم في الوضع البسيط: "
                f"{payload.get('permission_codename', payload.get('group', ''))} "
                f"→ {target_user.username}"
            ),
        )
    except (ImportError, LookupError, OperationalError, ProgrammingError):
        _strict_perm_logger.debug("AuditLog model not available or incompatible, skipping DB audit.", exc_info=True)
