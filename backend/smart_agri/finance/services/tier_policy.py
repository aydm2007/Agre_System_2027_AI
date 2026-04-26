from decimal import Decimal
from smart_agri.core.models.farm import Farm

class TierPolicy:
    """
    [AGRI-GUARDIAN Phase 2] Threshold Engine.
    Enforces maximum financial limits based on farm size tier.
    Ensures that SMALL, MEDIUM, and LARGE farms have governed ceilings for local approvals.
    """
    
    TIER_LIMITS = {
        Farm.TIER_SMALL: {
            "local_finance_threshold": Decimal("500000.0000"),
            "sector_review_threshold": Decimal("1000000.0000"),
            "procurement_committee_threshold": Decimal("2000000.0000"),
        },
        Farm.TIER_MEDIUM: {
            "local_finance_threshold": Decimal("2000000.0000"),
            "sector_review_threshold": Decimal("5000000.0000"),
            "procurement_committee_threshold": Decimal("10000000.0000"),
        },
        Farm.TIER_LARGE: {
            "local_finance_threshold": Decimal("10000000.0000"),
            "sector_review_threshold": Decimal("25000000.0000"),
            "procurement_committee_threshold": Decimal("50000000.0000"),
        },
    }

    @classmethod
    def resolve_thresholds(cls, farm, settings_obj) -> dict:
        """
        Calculates the effective thresholds by capping the requested FarmSettings
        values against the Farm's tier maximum limits.
        """
        tier = getattr(farm, 'tier', Farm.TIER_SMALL) or Farm.TIER_SMALL
        caps = cls.TIER_LIMITS.get(tier, cls.TIER_LIMITS[Farm.TIER_SMALL])

        req_local = getattr(settings_obj, "local_finance_threshold", Decimal("100000.0000"))
        req_sector = getattr(settings_obj, "sector_review_threshold", Decimal("250000.0000"))
        req_committee = getattr(settings_obj, "procurement_committee_threshold", Decimal("500000.0000"))

        local = min(req_local, caps["local_finance_threshold"])
        sector = min(req_sector, caps["sector_review_threshold"])
        committee = min(req_committee, caps["procurement_committee_threshold"])

        return {
            "local_finance_threshold": local,
            "sector_review_threshold": max(sector, local),
            "procurement_committee_threshold": max(committee, sector),
            "tier": tier,
        }
