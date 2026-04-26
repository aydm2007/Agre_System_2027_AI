from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

from smart_agri.core.services.audit_event_factory import AuditEventFactory


def log_sensitive_mutation(
    *,
    actor: Any,
    action: str,
    model_name: str,
    object_id: Any,
    reason: str,
    old_value: dict | None,
    new_value: dict | None,
    farm_id: int | None = None,
    context: dict | None = None,
) -> None:
    """
    [AGRI-GUARDIAN §Axis-7] Append-only forensic audit entry for sensitive
    finance/inventory mutations.

    Persists both old_payload (previous state) and new_payload (current state)
    to satisfy chain-of-custody requirements.
    """
    event = AuditEventFactory.build(
        actor=actor,
        action=action,
        model_name=model_name,
        object_id=object_id,
        reason=reason or "",
        farm_id=farm_id,
        source="sensitive_audit",
        category="sensitive_mutation",
        old_value=old_value or {},
        new_value=new_value or {},
        context=context or {},
    )
    AuditEventFactory.record(event)


def audit_financial_mutation(
    *,
    actor: Any,
    action: str,
    model_name: str,
    object_id: Any,
    farm_id: int | None = None,
    amount: Any = None,
    description: str = "",
    old_state: dict | None = None,
    new_state: dict | None = None,
) -> None:
    """
    [AGRI-GUARDIAN §Axis-7] Specialized audit helper for financial mutations.

    Automatically tags entries with 'financial_mutation' category and captures
    monetary amounts for forensic traceability.
    """
    from decimal import Decimal

    amount_str = str(amount) if amount is not None else "0"

    log_sensitive_mutation(
        actor=actor,
        action=action,
        model_name=model_name,
        object_id=object_id,
        reason=description or f"Financial mutation: {action}",
        old_value=old_state,
        new_value={
            **(new_state or {}),
            "amount": amount_str,
        },
        farm_id=farm_id,
        context={
            "source": "financial_mutation_audit",
            "amount": amount_str,
        },
    )
