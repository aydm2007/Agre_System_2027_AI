from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class IntegrationEvent:
    event_type: str
    aggregate_type: str
    aggregate_id: str
    farm_id: str | None = None
    occurred_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + 'Z')
    event_id: str = field(default_factory=lambda: str(uuid4()))
    version: str = '1.0'
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class FarmCreated(IntegrationEvent):
    def __init__(self, aggregate_id: str, farm_name: str, owner_id: str | None = None, **kwargs: Any) -> None:
        payload = {'farm_name': farm_name, 'owner_id': owner_id}
        payload.update(kwargs.pop('payload', {}))
        IntegrationEvent.__init__(self,
            event_type='farm.created',
            aggregate_type='farm',
            aggregate_id=str(aggregate_id),
            payload=payload,
            **kwargs,
        )


@dataclass(slots=True)
class ActivityLogged(IntegrationEvent):
    def __init__(self, aggregate_id: str, activity_type: str, quantity: float | int | None = None, **kwargs: Any) -> None:
        payload = {'activity_type': activity_type, 'quantity': quantity}
        payload.update(kwargs.pop('payload', {}))
        IntegrationEvent.__init__(self,
            event_type='activity.logged',
            aggregate_type='activity',
            aggregate_id=str(aggregate_id),
            payload=payload,
            **kwargs,
        )


@dataclass(slots=True)
class InventoryChanged(IntegrationEvent):
    def __init__(self, aggregate_id: str, sku: str, delta_quantity: float | int, **kwargs: Any) -> None:
        payload = {'sku': sku, 'delta_quantity': delta_quantity}
        payload.update(kwargs.pop('payload', {}))
        IntegrationEvent.__init__(self,
            event_type='inventory.changed',
            aggregate_type='inventory-item',
            aggregate_id=str(aggregate_id),
            payload=payload,
            **kwargs,
        )


@dataclass(slots=True)
class FinancialTransactionCreated(IntegrationEvent):
    def __init__(self, aggregate_id: str, amount: str, currency: str = 'YER', **kwargs: Any) -> None:
        payload = {'amount': amount, 'currency': currency}
        payload.update(kwargs.pop('payload', {}))
        IntegrationEvent.__init__(self,
            event_type='finance.transaction.created',
            aggregate_type='financial-transaction',
            aggregate_id=str(aggregate_id),
            payload=payload,
            **kwargs,
        )
