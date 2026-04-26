from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import logging

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from smart_agri.core.models import LocationIrrigationPolicy

logger = logging.getLogger(__name__)


class QuarantinedSyncError(ValidationError):
    """Raised when a mutation must be quarantined for governance review."""


ZAKAT_RATE_MAP = {
    "RAIN_10": Decimal("0.1000"),
    "WELL_5": Decimal("0.0500"),
    "MIXED_75": Decimal("0.0750"),
    "10_PERCENT": Decimal("0.1000"),  # legacy farm-level fallback
    "5_PERCENT": Decimal("0.0500"),   # legacy farm-level fallback
}


def get_zakat_policy_mode() -> str:
    raw = getattr(settings, "LOCATION_ZAKAT_POLICY_V2_MODE", "off") or "off"
    mode = str(raw).strip().lower()
    if mode not in {"off", "shadow", "enforce", "full"}:
        return "off"
    return mode


def is_v2_enabled() -> bool:
    return get_zakat_policy_mode() in {"shadow", "enforce", "full"}


def is_v2_hard_enforced() -> bool:
    return get_zakat_policy_mode() in {"enforce", "full"}


def normalize_business_date(value) -> date:
    if isinstance(value, datetime):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value.date()
    if isinstance(value, date):
        return value
    return timezone.localdate()


def resolve_zakat_policy_for_harvest(location, business_date: date):
    dt = normalize_business_date(business_date)
    policy = (
        LocationIrrigationPolicy.objects.filter(
            location_id=location.id,
            is_active=True,
            deleted_at__isnull=True,
        )
        .filter(
            Q(valid_daterange__contains=dt)
            | Q(valid_daterange__startswith=dt)
        )
        .order_by("-created_at")
        .first()
    )

    if policy:
        return policy

    if is_v2_hard_enforced():
        raise QuarantinedSyncError(
            f"No active location irrigation policy for location={location.id} date={dt}. "
            "Mutation quarantined pending finance policy approval."
        )

    logger.warning(
        "Zakat policy gap detected for location=%s date=%s while mode=%s; fallback permitted.",
        location.id,
        dt,
        get_zakat_policy_mode(),
    )
    return None


def resolve_zakat_rate(rule: str) -> Decimal:
    rate = ZAKAT_RATE_MAP.get(rule)
    if rate is None:
        raise ValidationError("Invalid zakat rule.")
    return rate

