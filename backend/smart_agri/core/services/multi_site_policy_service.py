from __future__ import annotations

"""V6 multi-site / offline-first policy helpers.

This module is intentionally lightweight so it can be imported in static checks
without requiring a full Django runtime. It provides one normalized contract for
site, sector, farm, and offline operation settings.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class OperationScope:
    sector_id: str | None = None
    site_id: str | None = None
    farm_id: int | None = None
    offline_enabled: bool = False
    queue_ttl_hours: int = 48
    sync_strategy: str = "deferred"
    escalation_channel: str = "operations"

    def snapshot(self) -> dict[str, Any]:
        return {
            "sector_id": self.sector_id,
            "site_id": self.site_id,
            "farm_id": self.farm_id,
            "offline_enabled": self.offline_enabled,
            "queue_ttl_hours": self.queue_ttl_hours,
            "sync_strategy": self.sync_strategy,
            "escalation_channel": self.escalation_channel,
        }


def resolve_operation_scope(
    *,
    sector_id: str | None = None,
    site_id: str | None = None,
    farm_id: int | None = None,
    offline_enabled: bool = False,
) -> OperationScope:
    return OperationScope(
        sector_id=sector_id,
        site_id=site_id,
        farm_id=farm_id,
        offline_enabled=offline_enabled,
        queue_ttl_hours=72 if offline_enabled else 24,
        sync_strategy="store-and-forward" if offline_enabled else "online-first",
        escalation_channel="regional-ops" if sector_id else "operations",
    )
