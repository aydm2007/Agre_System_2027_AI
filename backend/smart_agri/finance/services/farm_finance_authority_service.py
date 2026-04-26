from __future__ import annotations

from django.core.exceptions import ValidationError

from smart_agri.core.api.permissions import user_has_any_farm_role, user_has_farm_role
from smart_agri.core.models.settings import FarmSettings
from smart_agri.core.services.policy_engine_service import PolicyEngineService
from smart_agri.core.services.remote_review_service import RemoteReviewService


class FarmFinanceAuthorityService:
    """Policy-aware finance authority resolver for STRICT financial cycles."""

    FARM_FINANCE_MANAGER_ROLES = {
        "المدير المالي للمزرعة",
        "المدير المالي لقطاع المزارع",
        "مدير القطاع",
        "مدير النظام",
    }
    SMALL_FARM_ACTING_ROLES = {
        "رئيس الحسابات",
        "المدير المالي للمزرعة",
        "المدير المالي لقطاع المزارع",
        "مدير القطاع",
        "مدير النظام",
    }
    SECTOR_OVERRIDE_ROLES = {
        "محاسب القطاع",
        "مراجع القطاع",
        "رئيس حسابات القطاع",
        "المدير المالي لقطاع المزارع",
        "مدير القطاع",
        "مدير النظام",
    }

    @staticmethod
    def _settings(farm):
        settings_obj = getattr(farm, 'settings', None)
        return PolicyEngineService.runtime_settings_for_farm(farm=farm, settings_obj=settings_obj)

    @classmethod
    def _farm_tier(cls, farm) -> str:
        return (getattr(farm, 'tier', None) or 'SMALL').upper()

    @classmethod
    def strict_cycle_roles(cls, *, farm) -> set[str]:
        settings_obj = cls._settings(farm)
        roles = set(cls.FARM_FINANCE_MANAGER_ROLES)
        if cls._farm_tier(farm) == 'SMALL' and getattr(settings_obj, 'single_finance_officer_allowed', False):
            roles |= cls.SMALL_FARM_ACTING_ROLES
        return roles

    @classmethod
    def require_strict_cycle_authority(cls, *, user, farm, action_label: str, allow_sector_override: bool = True):
        settings_obj = cls._settings(farm)
        if getattr(settings_obj, 'mode', FarmSettings.MODE_SIMPLE) != FarmSettings.MODE_STRICT:
            raise ValidationError(f"{action_label} متاح فقط في الوضع الصارم (STRICT).")
            
        # [AGRI-GUARDIAN Axis 6] Runtime Defense in Depth for Farm Size Governance
        if cls._farm_tier(farm) in ['MEDIUM', 'LARGE']:
            from smart_agri.accounts.models import FarmMembership
            has_ffm = FarmMembership.objects.filter(
                farm_id=farm.id,
                role__in=cls.FARM_FINANCE_MANAGER_ROLES
            ).exists()
            if not has_ffm:
                raise ValidationError(f"🔴 [GOVERNANCE BLOCK] تم سحب/عدم وجود مدير مالي للمزرعة (الفئة: {cls._farm_tier(farm)}). لا يمكن تنفيذ {action_label} حتى يتم التعيين.")
                
        if getattr(settings_obj, 'remote_site', False) and getattr(settings_obj, 'weekly_remote_review_required', False):
            RemoteReviewService.enforce_finance_window(farm_settings=settings_obj)
        roles = cls.strict_cycle_roles(farm=farm)
        if allow_sector_override:
            roles |= cls.SECTOR_OVERRIDE_ROLES
        if user_has_farm_role(user, farm.id, roles):
            return
        if user_has_any_farm_role(user, roles):
            return
        raise ValidationError(f"{action_label} يتطلب صلاحية مالية STRICT على مستوى المزرعة/القطاع.")

    @classmethod
    def require_profiled_posting_authority(cls, *, user, farm, action_label: str):
        """
        Applies strict final approval when the farm uses the strict_finance profile;
        otherwise falls back to governed STRICT cycle authority.
        """
        settings_obj = cls._settings(farm)
        approval_profile = getattr(settings_obj, 'approval_profile', FarmSettings.APPROVAL_PROFILE_TIERED)
        if approval_profile == FarmSettings.APPROVAL_PROFILE_STRICT_FINANCE:
            cls.require_sector_final_authority(user=user, farm=farm, action_label=action_label)
            return
        cls.require_strict_cycle_authority(user=user, farm=farm, action_label=action_label)

    @classmethod
    def require_sector_final_authority(cls, *, user, farm, action_label: str):
        roles = {"رئيس حسابات القطاع", "المدير المالي لقطاع المزارع", "مدير القطاع", "مدير النظام"}
        if user_has_farm_role(user, farm.id, roles) or user_has_any_farm_role(user, roles):
            return
        raise ValidationError(f"{action_label} يتطلب اعتماداً قطاعياً نهائياً.")

    @classmethod
    def role_governance_snapshot(cls, *, farm) -> dict:
        settings_obj = cls._settings(farm)
        return {
            'farm_id': getattr(farm, 'id', None),
            'farm_tier': cls._farm_tier(farm),
            'approval_profile': getattr(settings_obj, 'approval_profile', FarmSettings.APPROVAL_PROFILE_TIERED),
            'remote_site': bool(getattr(settings_obj, 'remote_site', False)),
            'strict_cycle_roles': sorted(cls.strict_cycle_roles(farm=farm)),
            'sector_final_roles': sorted({'رئيس حسابات القطاع', 'المدير المالي لقطاع المزارع', 'مدير القطاع', 'مدير النظام'}),
        }
