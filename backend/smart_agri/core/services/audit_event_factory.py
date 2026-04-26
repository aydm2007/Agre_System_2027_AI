from __future__ import annotations

"""Centralized factory for forensic-grade audit events.

V6 goal:
- unify high-risk mutation auditing behind one contract
- keep metadata shape stable across finance / operations / governance flows
- preserve append-only semantics by delegating persistence to AuditLog.create
"""

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class AuditEvent:
    actor: Any
    action: str
    model: str
    object_id: str
    reason: str = ""
    farm_id: int | None = None
    source: str = "application"
    mode: str | None = None
    category: str = "sensitive_mutation"
    old_value: dict[str, Any] = field(default_factory=dict)
    new_value: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)

    def to_payloads(self) -> tuple[dict[str, Any], dict[str, Any]]:
        old_payload = {
            "farm_id": self.farm_id,
            "old_value": self.old_value,
        }
        new_payload = {
            "forensic": True,
            "category": self.category,
            "farm_id": self.farm_id,
            "source": self.source,
            "mode": self.mode,
            "reason": self.reason,
            "new_value": self.new_value,
            "context": self.context,
        }
        return old_payload, new_payload


class AuditEventFactory:
    @staticmethod
    def build(
        *,
        actor: Any,
        action: str,
        model_name: str,
        object_id: Any,
        reason: str = "",
        farm_id: int | None = None,
        source: str = "application",
        mode: str | None = None,
        category: str = "sensitive_mutation",
        old_value: dict[str, Any] | None = None,
        new_value: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> AuditEvent:
        return AuditEvent(
            actor=actor,
            action=action,
            model=model_name,
            object_id=str(object_id or ""),
            reason=reason or "",
            farm_id=farm_id,
            source=source,
            mode=mode,
            category=category,
            old_value=old_value or {},
            new_value=new_value or {},
            context=context or {},
        )

    @staticmethod
    def record(event: AuditEvent) -> None:
        from smart_agri.core.models.log import AuditLog

        old_payload, new_payload = event.to_payloads()
        AuditLog.objects.create(
            actor=event.actor if getattr(event.actor, "is_authenticated", False) else None,
            action=event.action,
            model=event.model,
            object_id=event.object_id,
            old_payload=old_payload,
            new_payload=new_payload,
            reason=event.reason or "",
        )

    @staticmethod
    def describe(event: AuditEvent) -> dict[str, Any]:
        return asdict(event)
