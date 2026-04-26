from __future__ import annotations

import os

from .base import ConnectorDescriptor


class MarketConnector:
    def describe(self) -> dict[str, str | bool]:
        configured = bool(os.getenv('MARKET_PRICES_URL'))
        return ConnectorDescriptor(
            name='market',
            ready=configured,
            mode='http-pull',
            notes='Set MARKET_PRICES_URL to enrich procurement and pricing decisions.',
        ).to_dict()
