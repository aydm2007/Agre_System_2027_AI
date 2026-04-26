from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Protocol

from .event_contracts import IntegrationEvent


class OutboxStatus(str, Enum):
    PENDING = 'pending'
    DISPATCHED = 'dispatched'
    FAILED = 'failed'


@dataclass(slots=True)
class OutboxMessage:
    event: IntegrationEvent
    destination: str
    status: OutboxStatus = OutboxStatus.PENDING
    attempts: int = 0
    last_error: str | None = None

    def mark_dispatched(self) -> None:
        self.status = OutboxStatus.DISPATCHED
        self.last_error = None

    def mark_failed(self, exc: Exception) -> None:
        self.status = OutboxStatus.FAILED
        self.attempts += 1
        self.last_error = str(exc)


class Publisher(Protocol):
    def publish(self, destination: str, payload: dict) -> None: ...


@dataclass
class OutboxDispatcher:
    publisher: Publisher
    queue: list[OutboxMessage] = field(default_factory=list)

    def enqueue(self, message: OutboxMessage) -> OutboxMessage:
        self.queue.append(message)
        return message

    def pending(self) -> Iterable[OutboxMessage]:
        return [item for item in self.queue if item.status == OutboxStatus.PENDING]

    def dispatch_pending(self) -> list[OutboxMessage]:
        processed: list[OutboxMessage] = []
        for message in list(self.pending()):
            try:
                self.publisher.publish(message.destination, message.event.to_dict())
                message.mark_dispatched()
            except (TimeoutError, ConnectionError, OSError, ValueError, RuntimeError) as exc:  # pragma: no cover - connector failures are integration specific
                message.mark_failed(exc)
            processed.append(message)
        return processed


def build_outbox_message(event: IntegrationEvent, destination: str) -> OutboxMessage:
    return OutboxMessage(event=event, destination=destination)
