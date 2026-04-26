from __future__ import annotations

import os
from functools import lru_cache

from .outbox import OutboxDispatcher
from .publishers import CompositePublisher, LoggingPublisher, MemoryPublisher, ReadinessEvidencePublisher, WebhookPublisher


@lru_cache(maxsize=1)
def get_publisher():
    mode = os.getenv('INTEGRATION_HUB_PUBLISHER', 'composite').strip().lower()
    if mode == 'memory':
        return MemoryPublisher()
    if mode == 'readiness_evidence':
        return ReadinessEvidencePublisher()
    if mode == 'readiness_composite':
        return CompositePublisher([
            LoggingPublisher(),
            ReadinessEvidencePublisher(),
        ], name='readiness_composite')
    if mode == 'webhook':
        endpoint_base = os.getenv('INTEGRATION_HUB_WEBHOOK_BASE', 'http://localhost:9000/integration-events')
        timeout_seconds = int(os.getenv('INTEGRATION_HUB_WEBHOOK_TIMEOUT_SECONDS', '5'))
        return WebhookPublisher(endpoint_base=endpoint_base, timeout_seconds=timeout_seconds)
    if mode in {'dual', 'composite'}:
        endpoint_base = os.getenv('INTEGRATION_HUB_WEBHOOK_BASE', 'http://localhost:9000/integration-events')
        return CompositePublisher([
            LoggingPublisher(),
            WebhookPublisher(endpoint_base=endpoint_base, timeout_seconds=int(os.getenv('INTEGRATION_HUB_WEBHOOK_TIMEOUT_SECONDS', '5'))),
        ])
    return LoggingPublisher()


@lru_cache(maxsize=1)
def get_dispatcher() -> OutboxDispatcher:
    return OutboxDispatcher(publisher=get_publisher())


def reset_registry() -> None:
    get_dispatcher.cache_clear()
    get_publisher.cache_clear()


def integration_hub_snapshot() -> dict:
    dispatcher = get_dispatcher()
    publisher = get_publisher()
    queue = list(dispatcher.queue)
    status_counts: dict[str, int] = {}
    for item in queue:
        status_counts[item.status.value] = status_counts.get(item.status.value, 0) + 1
    describe = publisher.describe() if hasattr(publisher, 'describe') else {'name': getattr(publisher, 'name', publisher.__class__.__name__.lower())}
    return {
        'publisher': describe,
        'queued_messages': len(queue),
        'pending_messages': len(list(dispatcher.pending())),
        'status_counts': status_counts,
    }
