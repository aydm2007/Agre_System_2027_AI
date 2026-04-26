from __future__ import annotations

import logging

from django.core.exceptions import ValidationError
from django.db import DatabaseError

logger = logging.getLogger(__name__)


class FarmTieringPolicyService:
    """Runtime policy map for farm tiers so tiering is not documentation-only.

    [PRD V21 §8 / AGENTS.md L19 / ROLE_PERMISSION_MATRIX §4]
    Enforces:
    - SMALL: single_finance_officer_allowed with compensating controls
    - MEDIUM: requires dedicated المدير المالي للمزرعة
    - LARGE: requires dedicated المدير المالي للمزرعة + stronger segregation
    """

    TIER_MATRIX = {
        "small": {
            "label_ar": "صغيرة",
            "approval_levels": 1,
            "delegation_levels": 1,
            "finance_model": "single_officer_allowed",
            "requires_farm_finance_manager": False,
            "sector_review_default": True,
        },
        "medium": {
            "label_ar": "متوسطة",
            "approval_levels": 3,
            "delegation_levels": 2,
            "finance_model": "farm_finance_manager_required",
            "requires_farm_finance_manager": True,
            "sector_review_default": True,
        },
        "large": {
            "label_ar": "كبرى",
            "approval_levels": 5,
            "delegation_levels": 3,
            "finance_model": "full_sector_chain",
            "requires_farm_finance_manager": True,
            "sector_review_default": True,
        },
        # backward compatibility
        "basic": {
            "label_ar": "صغيرة",
            "approval_levels": 1,
            "delegation_levels": 1,
            "finance_model": "single_officer_allowed",
            "requires_farm_finance_manager": False,
            "sector_review_default": True,
        },
        "advanced": {
            "label_ar": "متوسطة",
            "approval_levels": 3,
            "delegation_levels": 2,
            "finance_model": "farm_finance_manager_required",
            "requires_farm_finance_manager": True,
            "sector_review_default": True,
        },
        "enterprise": {
            "label_ar": "كبرى",
            "approval_levels": 5,
            "delegation_levels": 3,
            "finance_model": "full_sector_chain",
            "requires_farm_finance_manager": True,
            "sector_review_default": True,
        },
    }

    # Role identifier used in FarmMembership for the Farm Finance Manager
    FFM_ROLE_NAME = "farm_finance_manager"

    @classmethod
    def snapshot(cls, tier: str | None) -> dict:
        resolved = (tier or "small").strip().lower()
        return {"tier": resolved, **cls.TIER_MATRIX.get(resolved, cls.TIER_MATRIX["small"])}

    @classmethod
    def snapshot_tier_policy(cls, tier: str | None) -> dict:
        # Compatibility alias kept for governance suites that still reference the older helper name.
        return cls.snapshot(tier)

    @classmethod
    def is_enterprise_ready(cls, tier: str | None, *, approvals_count: int, delegated_roles: int) -> bool:
        snap = cls.snapshot(tier)
        return approvals_count >= snap["approval_levels"] and delegated_roles >= snap["delegation_levels"]

    @classmethod
    def validate_finance_authority(cls, *, farm) -> None:
        """Enforce PRD §8.2/8.3 + ROLE_PERMISSION_MATRIX §4:

        MEDIUM/LARGE farms MUST have a dedicated Farm Finance Manager
        (المدير المالي للمزرعة). If missing, financial approval creation
        and governed posting actions must be blocked.

        Raises:
            ValidationError: if farm tier requires FFM but none is assigned.
        """
        from smart_agri.core.models.settings import FarmSettings

        try:
            farm_settings = FarmSettings.objects.filter(farm=farm).first()
        except DatabaseError:
            farm_settings = None

        tier = getattr(farm_settings, "farm_tier", None) or getattr(farm, "tier", None) or "small"
        snap = cls.snapshot(tier)

        if not snap.get("requires_farm_finance_manager"):
            return  # SMALL farms: single finance officer allowed

        # Check if FFM role is assigned in FarmMembership
        try:
            from smart_agri.accounts.models import FarmMembership
            has_ffm = FarmMembership.objects.filter(
                farm=farm,
                role__name__icontains=cls.FFM_ROLE_NAME,
            ).exists()
        except (ImportError, Exception) as exc:
            logger.warning(
                "Cannot verify FFM role for farm %s (tier=%s): %s",
                getattr(farm, "id", "?"), tier, exc,
            )
            # Fail-safe: require explicit FFM presence
            has_ffm = False

        if not has_ffm:
            raise ValidationError(
                f"المزرعة ({snap['label_ar']}) تتطلب تعيين المدير المالي للمزرعة "
                f"(Farm Finance Manager) قبل إنشاء طلبات الاعتماد المالي. "
                f"[PRD V21 §8 / ROLE_PERMISSION_MATRIX §4]"
            )
