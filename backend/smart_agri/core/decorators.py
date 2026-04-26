import logging
from functools import wraps
from django.core.exceptions import PermissionDenied
from smart_agri.core.models.settings import FarmSettings

logger = logging.getLogger(__name__)


def enforce_strict_mode(farm):
    """
    [AGRI-GUARDIAN Axis 4 & 10]
    Service Layer Guard: Hard blocker for STRICT-only service operations.
    Call this at the top of any @staticmethod financial service method.

    Usage:
        @staticmethod
        @transaction.atomic
        def create_request(*, farm, ...):
            enforce_strict_mode(farm)
            ...
    """
    if farm is None:
        logger.warning("🔴 [FORENSIC BLOCK] enforce_strict_mode called with farm=None. Denying.")
        raise PermissionDenied(
            "🔴 [FORENSIC BLOCK] المزرعة غير محددة. لا يمكن تنفيذ العملية المالية."
        )

    farm_id = getattr(farm, 'pk', farm)
    try:
        settings = FarmSettings.objects.get(farm_id=farm_id)
    except FarmSettings.DoesNotExist:
        logger.warning(f"🔴 [FORENSIC BLOCK] FarmSettings not found for farm {farm_id}. Denying.")
        raise PermissionDenied(
            "🔴 [FORENSIC BLOCK] إعدادات المزرعة غير موجودة. لا يمكن تنفيذ العملية المالية."
        )

    if settings.mode != FarmSettings.MODE_STRICT:
        logger.warning(
            f"🔴 [FORENSIC BLOCK] Financial service operation blocked: "
            f"Farm {farm_id} is in {settings.mode} mode. STRICT mode required."
        )
        raise PermissionDenied(
            "🔴 [FORENSIC BLOCK] هذه العملية المالية تتطلب تفعيل النظام المالي الصارم (STRICT). "
            "المزرعة حالياً في وضع SIMPLE."
        )


def require_strict_mode(func):
    """
    [AGRI-GUARDIAN Axis 4]
    Service Layer Decorator to enforce STRICT mode at the deepest level.
    Prevents any service from executing financial modifications if the farm is in SIMPLE mode.
    Works with both instance methods (self.farm) and functions that receive farm as kwarg.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Try to extract farm from various sources
        farm = kwargs.get('farm') or kwargs.get('farm_id')

        # If first arg is 'self', check self.farm
        if not farm and args:
            obj = args[0]
            farm = getattr(obj, 'farm', None) or getattr(obj, 'farm_id', None)

        if farm:
            enforce_strict_mode(farm)

        return func(*args, **kwargs)
    return wrapper
