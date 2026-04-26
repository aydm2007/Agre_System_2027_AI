from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Protocol
from urllib import request as urllib_request

logger = logging.getLogger(__name__)


class IntegrationPublisher(Protocol):
    name: str

    def publish(self, destination: str, payload: dict) -> None: ...

    def describe(self) -> dict:
        return {"name": getattr(self, "name", self.__class__.__name__.lower())}


@dataclass
class LoggingPublisher:
    name: str = 'logging'

    def publish(self, destination: str, payload: dict) -> None:
        logger.info('integration_hub.publish', extra={'destination': destination, 'payload': payload})


@dataclass
class MemoryPublisher:
    name: str = 'memory'
    published: list[dict] = field(default_factory=list)

    def publish(self, destination: str, payload: dict) -> None:
        self.published.append({'destination': destination, 'payload': payload})

    def describe(self) -> dict:
        return {'name': self.name, 'published_count': len(self.published)}


@dataclass
class ReadinessEvidencePublisher:
    name: str = 'readiness_evidence'
    published: list[dict] = field(default_factory=list)

    def publish(self, destination: str, payload: dict) -> None:
        self.published.append({'destination': destination, 'payload': payload})
        if destination.startswith('readiness/retry'):
            raise RuntimeError('readiness_retryable_failure')
        if destination.startswith('readiness/dead-letter'):
            raise RuntimeError('readiness_dead_letter_failure')

    def describe(self) -> dict:
        return {'name': self.name, 'published_count': len(self.published)}


@dataclass
class WebhookPublisher:
    endpoint_base: str
    timeout_seconds: int = 5
    name: str = 'webhook'

    def publish(self, destination: str, payload: dict) -> None:
        body = json.dumps(payload).encode('utf-8')
        target = f"{self.endpoint_base.rstrip('/')}/{destination.lstrip('/')}"
        req = urllib_request.Request(
            target,
            data=body,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        with urllib_request.urlopen(req, timeout=self.timeout_seconds) as response:  # nosec - integration endpoint is configured by operator
            if response.status >= 400:
                raise RuntimeError(f'Webhook publish failed with status {response.status}')

    def describe(self) -> dict:
        return {'name': self.name, 'endpoint_base': self.endpoint_base, 'timeout_seconds': self.timeout_seconds}


@dataclass
class CompositePublisher:
    publishers: list[IntegrationPublisher]
    name: str = 'composite'

    def publish(self, destination: str, payload: dict) -> None:
        for publisher in self.publishers:
            publisher.publish(destination, payload)

    def describe(self) -> dict:
        return {'name': self.name, 'publishers': [p.describe() if hasattr(p, 'describe') else {'name': getattr(p, 'name', p.__class__.__name__.lower())} for p in self.publishers]}
