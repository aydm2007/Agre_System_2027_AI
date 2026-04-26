from __future__ import annotations

import os

from .base import ConnectorDescriptor


class IoTConnector:
    def describe(self) -> dict[str, str | bool]:
        configured = bool(os.getenv('IOT_GATEWAY_URL'))
        return ConnectorDescriptor(
            name='iot',
            ready=configured,
            mode='event-ingest',
            notes='Set IOT_GATEWAY_URL to enable pump/sensor telemetry ingestion.',
        ).to_dict()
