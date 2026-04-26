from __future__ import annotations

import os

from .base import ConnectorDescriptor


class WeatherConnector:
    def describe(self) -> dict[str, str | bool]:
        configured = bool(os.getenv('WEATHER_API_BASE_URL'))
        return ConnectorDescriptor(
            name='weather',
            ready=configured,
            mode='http-pull',
            notes='Set WEATHER_API_BASE_URL to enable live weather enrichment.',
        ).to_dict()
