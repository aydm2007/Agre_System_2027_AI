from __future__ import annotations

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .connectors.iot_connector import IoTConnector
from .connectors.market_connector import MarketConnector
from .connectors.weather_connector import WeatherConnector
from .registry import integration_hub_snapshot
from .persistence import persistent_outbox_snapshot


@api_view(['GET'])
@permission_classes([AllowAny])
def integration_hub_status(request):
    connectors = {
        'weather': WeatherConnector().describe(),
        'iot': IoTConnector().describe(),
        'market': MarketConnector().describe(),
    }
    ready = all(item.get('ready') for item in connectors.values())
    return Response({
        'status': 'ok' if ready else 'degraded',
        'hub': 'integration-hub',
        'connectors': connectors,
        'outbox_pattern': 'enabled',
        'event_contracts': ['farm.created', 'activity.logged', 'inventory.changed', 'finance.transaction.created'],
        'persistent_outbox': persistent_outbox_snapshot(),
    }, status=200 if ready else 503)


@api_view(['GET'])
@permission_classes([AllowAny])
def integration_hub_diagnostics(request):
    snapshot = integration_hub_snapshot()
    return Response({
        'status': 'ok',
        'hub': 'integration-hub',
        'request_id': getattr(request, 'request_id', None),
        'farm_scope_hint': getattr(request, 'farm_scope_hint', None),
        'snapshot': snapshot,
        'persistent_outbox': persistent_outbox_snapshot(),
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def integration_hub_outbox_status(request):
    return Response({
        'status': 'ok',
        'hub': 'integration-hub',
        'persistent_outbox': persistent_outbox_snapshot(),
    })
