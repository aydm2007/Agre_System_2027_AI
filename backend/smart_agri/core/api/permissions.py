"""
API Permissions Module
"""
from rest_framework import permissions
from django.utils import timezone
from smart_agri.core.models import Farm
from smart_agri.accounts.models import FarmMembership, RoleDelegation


MANAGER_ROLES = {
    "مدير المزرعة",
    "المدير المالي للمزرعة",
    "رئيس الحسابات",
    "رئيس حسابات القطاع",
    "المدير المالي لقطاع المزارع",
    "مدير القطاع",
    "مدير النظام",
    "Manager",
    "Farm Manager",
    "Finance Manager",
    "Chief Accountant",
    "Sector Chief Accountant",
    "Sector Finance Director",
    "Sector Director",
    "System Manager",
}

# Roles allowed to POST/PUT/PATCH (write operations)
WRITE_ROLES = MANAGER_ROLES | {
    "مشرف ميداني",
    "المهندس الزراعي",
    "فني زراعي",
    "مدخل بيانات",
    "أمين مخزن",
}
# Roles allowed to DELETE
DELETE_ROLES = MANAGER_ROLES | {
    "رئيس الحسابات",
    "مدير النظام",
}

SECTOR_FINANCE_GROUPS = {
    "رئيس حسابات القطاع",
    "المدير المالي لقطاع المزارع",
}


class IsFarmManager(permissions.BasePermission):
    """Permission class that checks if user has manager-level access.

    Checks three sources per AGENTS.md Axis 10:
    1. Django groups (legacy path)
    2. FarmMembership.role (primary source of truth)
    3. Active RoleDelegation (temporary authority)
    """

    def has_permission(self, request, view) -> bool:
        user = getattr(request, 'user', None)
        if not user or not getattr(user, "is_authenticated", False):
            return False
        if getattr(user, "is_superuser", False):
            return True
        # 1. Django groups (legacy)
        if user.groups.filter(name__in=MANAGER_ROLES).exists():
            return True
        # 2. FarmMembership.role (primary)
        if FarmMembership.objects.filter(user=user, role__in=MANAGER_ROLES).exists():
            return True
        # 3. Active RoleDelegation (temporary authority per Axis 10)
        now = timezone.now()
        return RoleDelegation.objects.filter(
            delegate_user=user,
            role__in=MANAGER_ROLES,
            is_active=True,
            starts_at__lte=now,
            ends_at__gte=now,
        ).exists()
        

class StrictErpOnlyPermission(permissions.BasePermission):
    """
    [AGRI-GUARDIAN] Axis 15 Compliance: Mode-locked Mutations.
    Restricts write operations to farms configured in MODE_STRICT.
    SIMPLE mode farms are treated as read-only technical control surfaces for these resources.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        if user.is_superuser:
            return True
            
        farm_id = None
        if hasattr(view, '_get_requested_farm_id'):
            farm_id = view._get_requested_farm_id()
        
        # If no specific farm identified for a global resource (like Item), 
        # we check if the user has ANY farm in STRICT mode. 
        # However, for Items, it's safer to allow only System Admins or 
        # require an explicit farm context if we want to tie it to a contract.
        # For now, we allow if any associated farm is STRICT.
        from smart_agri.core.models.settings import FarmSettings
        allowed_farms = user_farm_ids(user)
        if not allowed_farms:
            return False
            
        return FarmSettings.objects.filter(
            farm_id__in=allowed_farms, 
            mode=FarmSettings.MODE_STRICT
        ).exists()


class FarmScopedPermission(permissions.BasePermission):
    """Permission class that checks farm-level access."""
    SAFE = ("GET", "HEAD", "OPTIONS")
    _STANDARD_ACTIONS = {"create", "list", "retrieve", "update", "partial_update", "destroy"}

    def has_permission(self, request, view) -> bool:
        user = getattr(request, 'user', None)
        if request.method in self.SAFE:
            return bool(user and user.is_authenticated)
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        group_roles = set(group.name for group in user.groups.all())
        if group_roles & MANAGER_ROLES:
            return True
        if request.method in ("POST", "PUT", "PATCH"):
            if FarmMembership.objects.filter(
                user=user,
                role__in=WRITE_ROLES,
            ).exists():
                return True
        if request.method == "DELETE":
            if FarmMembership.objects.filter(user=user, role__in=DELETE_ROLES).exists():
                return True

        action = getattr(view, "action", None)
        if action and action not in self._STANDARD_ACTIONS:
            # Custom detail actions rely on object permissions once the entity is resolved.
            return True

        action_map = {'POST': "add", 'PUT': "change", 'PATCH': "change", 'DELETE': "delete"}
        perm_action = action_map.get(request.method)

        model = None
        queryset = getattr(view, 'queryset', None)
        if queryset is not None:
            model = getattr(queryset, 'model', None)
        if model is None:
            serializer_class = getattr(view, 'serializer_class', None)
            meta = getattr(serializer_class, 'Meta', None) if serializer_class else None
            model = getattr(meta, 'model', None) if meta else None

        if perm_action and model is not None:
            perm_name = f"{model._meta.app_label}.{perm_action}_{model._meta.model_name}"
            # Django Global Permissions check (fallback)
            if user.has_perm(perm_name):
                return True

        # SCOPED CHECK: Determine the context farm
        # NOTE: This requires the view to populate `request.farm` or provide a `farm_id` in kwargs
        # If we cannot determine the farm, we must default to DENY for safety in Strict Mode.
        # However, for general endpoints, we iterate user roles.
        # But for 'Privilege Escalation' fix, we must ensure the role applies to the TARGET farm.
        
        # We attempt to resolve farm_id from view kwargs (common pattern)
        farm_ids = set()
        if 'farm_pk' in view.kwargs:
             farm_ids.add(view.kwargs['farm_pk'])
        elif 'pk' in view.kwargs and model == Farm:
             farm_ids.add(view.kwargs['pk'])
        
        # If we identified a specific target farm, we check role ONLY for that farm.
        if farm_ids:
             roles = set(FarmMembership.objects.filter(user=user, farm_id__in=farm_ids).values_list('role', flat=True))
        else:
             # Strict mode: reject cross-farm writes when target farm context is unknown.
             return False

        if request.method == "DELETE":
            return bool(roles & DELETE_ROLES) or user.has_perm('core.delete_activity')
        if request.method in ("POST", "PUT", "PATCH"):
            return bool(roles & WRITE_ROLES)
        return False

    def has_object_permission(self, request, view, obj):
        user = getattr(request, 'user', None)
        if request.method in self.SAFE:
            return True
        if not user or not getattr(user, "is_authenticated", False):
            return False
        if getattr(user, "is_superuser", False):
            return True
        group_roles = set(group.name for group in user.groups.all())
        if group_roles & MANAGER_ROLES:
            return True

        farm_id = self._resolve_farm_id(obj)
        if farm_id is None:
            return False
        roles = set(
            FarmMembership.objects.filter(user=user, farm_id=farm_id).values_list("role", flat=True)
        )
        if request.method == "DELETE":
            return bool(roles & DELETE_ROLES) or user.has_perm('core.delete_activity')
        return bool(roles & WRITE_ROLES)

    def _resolve_farm_id(self, obj):
        if obj is None:
            return None
        if isinstance(obj, Farm):
            return obj.id
        farm_id = getattr(obj, "farm_id", None)
        if farm_id:
            return farm_id
        farm = getattr(obj, "farm", None)
        if getattr(farm, "id", None):
            return farm.id
            
        log = getattr(obj, "log", None)
        if log:
            return getattr(log, "farm_id", None)
            
        location = getattr(obj, "location", None)
        if location:
            return getattr(location, "farm_id", None)
            
        # fallback to checking first location in multilocations if it exists
        activity_locations = getattr(obj, "activity_locations", None)
        if activity_locations and hasattr(activity_locations, "first"):
            first_loc = activity_locations.first()
            if first_loc and first_loc.location:
                return first_loc.location.farm_id
                
        return None


def user_farm_ids(user):
    """Get list of farm IDs accessible by user."""
    if not user.is_authenticated:
        return []

    if user.is_superuser:
        membership_ids = list(
            FarmMembership.objects.filter(user=user).values_list("farm_id", flat=True)
        )
        if membership_ids:
            return membership_ids
        return list(Farm.objects.values_list("id", flat=True))
        
    return list(FarmMembership.objects.filter(user=user).values_list("farm_id", flat=True))


def _user_is_farm_manager(user):
    """Check if user has manager-level access.

    Checks all three authority sources per AGENTS.md Axis 10:
    1. Django groups (legacy)
    2. FarmMembership.role (primary)
    3. Active RoleDelegation (temporary authority)
    """
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    # 1. Django groups (legacy)
    if user.groups.filter(name__in=MANAGER_ROLES).exists():
        return True
    # 2. FarmMembership.role (primary)
    if FarmMembership.objects.filter(user=user, role__in=MANAGER_ROLES).exists():
        return True
    # 3. Active RoleDelegation (temporary authority)
    now = timezone.now()
    return RoleDelegation.objects.filter(
        delegate_user=user,
        role__in=MANAGER_ROLES,
        is_active=True,
        starts_at__lte=now,
        ends_at__gte=now,
    ).exists()


def user_has_farm_role(user, farm_id, roles):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    if FarmMembership.objects.filter(user=user, farm_id=farm_id, role__in=set(roles)).exists():
        return True
    now = timezone.now()
    return RoleDelegation.objects.filter(
        delegate_user=user,
        farm_id=farm_id,
        role__in=set(roles),
        is_active=True,
        starts_at__lte=now,
        ends_at__gte=now,
    ).exists()


def user_has_any_farm_role(user, roles):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    if FarmMembership.objects.filter(user=user, role__in=set(roles)).exists():
        return True
    now = timezone.now()
    return RoleDelegation.objects.filter(
        delegate_user=user,
        role__in=set(roles),
        is_active=True,
        starts_at__lte=now,
        ends_at__gte=now,
    ).exists()


def user_has_sector_finance_authority(user):
    """Sector-level financial authority for hard-close/final financial approvals."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    if user.has_perm("finance.can_hard_close_period") or user.has_perm("finance.can_sector_finance_approve"):
        return True
    group_roles = set(group.name for group in user.groups.all())
    return bool(group_roles & SECTOR_FINANCE_GROUPS)


def _ensure_user_has_farm_access(user, farm_id):
    """Raise PermissionDenied if user lacks access to farm."""
    from rest_framework.exceptions import PermissionDenied
    
    if farm_id is None:
        return
    if not user.is_authenticated:
        raise PermissionDenied("يجب تسجيل الدخول أولاً.")
    if user.is_superuser:
        return
    roles = set(group.name for group in user.groups.all())
    if roles & MANAGER_ROLES:
        return
    allowed = getattr(user, '_farm_ids_cache', None)
    if allowed is None:
        allowed = set(user_farm_ids(user))
        setattr(user, '_farm_ids_cache', allowed)
    try:
        farm_key = int(farm_id)
    except (TypeError, ValueError):
        farm_key = farm_id
    if farm_key not in allowed:
        raise PermissionDenied("لا تملك صلاحية الوصول إلى هذه المزرعة.")


def _limit_queryset_to_user_farms(queryset, user, lookup):
    """Filter queryset to only include farms user has access to."""
    if user.is_superuser:
        return queryset
    farm_ids = user_farm_ids(user)
    if not farm_ids:
        return queryset.none()
    return queryset.filter(**{lookup: farm_ids})
