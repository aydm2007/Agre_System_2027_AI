from __future__ import annotations

import os
from typing import Any

from django.conf import settings
from django.core.cache import InvalidCacheBackendError, cache
from django.db import DatabaseError, OperationalError, connection
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.http import HttpResponse
from rest_framework.response import Response

from smart_agri.core.platform_metrics import platform_metrics
from smart_agri.integration_hub.registry import integration_hub_snapshot
from smart_agri.integration_hub.persistence import persistent_outbox_snapshot


def _safe_cache_probe() -> dict[str, Any]:
    backend_name = getattr(settings, 'CACHES', {}).get('default', {}).get('BACKEND', 'unknown')
    payload = {'backend': backend_name, 'status': 'disabled'}
    try:
        cache.set('agri:readyz', 'ok', 5)
        payload['status'] = 'ok' if cache.get('agri:readyz') == 'ok' else 'degraded'
    except (InvalidCacheBackendError, ConnectionError, TimeoutError, ValueError, RuntimeError) as exc:
        payload['status'] = 'error'
        payload['error'] = str(exc)
    return payload


def _safe_db_probe() -> dict[str, Any]:
    payload = {'status': 'unknown'}
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        payload['status'] = 'ok'
        payload['vendor'] = connection.vendor
    except (DatabaseError, OperationalError, ValueError, RuntimeError) as exc:
        payload['status'] = 'error'
        payload['error'] = str(exc)
    return payload


@api_view(['GET'])
@permission_classes([AllowAny])
def livez(request):
    return Response({
        'status': 'ok',
        'service': 'agriasset-backend',
        'app_version': getattr(settings, 'APP_VERSION', os.getenv('APP_VERSION', '2.0.0')),
        'environment': os.getenv('SERVER_ENV', 'development'),
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def readyz(request):
    db = _safe_db_probe()
    cache_status = _safe_cache_probe()
    overall = 'ok' if db.get('status') == 'ok' and cache_status.get('status') in {'ok', 'disabled', 'degraded'} else 'degraded'
    return Response({
        'status': overall,
        'database': db,
        'cache': cache_status,
        'broker_configured': bool(getattr(settings, 'CELERY_BROKER_URL', '')),
    }, status=200 if overall == 'ok' else 503)


@api_view(['GET'])
@permission_classes([AllowAny])
def metrics_summary(request):
    domain_counts = {}
    try:
        from smart_agri.core.models.log import DailyLog
        from smart_agri.core.models.activity import Activity
        from smart_agri.core.models.farm import Farm
        domain_counts = {
            'farms': Farm.objects.count(),
            'daily_logs': DailyLog.objects.count(),
            'activities': Activity.objects.count(),
        }
    except (DatabaseError, OperationalError, ImportError, RuntimeError) as exc:  # pragma: no cover
        domain_counts = {'error': str(exc)}

    return Response({
        'service': 'agriasset-backend',
        'app_version': getattr(settings, 'APP_VERSION', os.getenv('APP_VERSION', '2.0.0')),
        'environment': os.getenv('SERVER_ENV', 'development'),
        'timestamp': timezone.now().isoformat(),
        'request_id': getattr(request, 'request_id', None),
        'integration_hub': integration_hub_snapshot(),
        'persistent_outbox': persistent_outbox_snapshot(),
        'observability': {
            'sentry_enabled': bool(os.getenv('SENTRY_DSN')),
            'cache_backend': getattr(settings, 'CACHES', {}).get('default', {}).get('BACKEND', 'unknown'),
            'celery_eager': bool(getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False)),
            'strict_farm_scope_headers': os.getenv('STRICT_FARM_SCOPE_HEADERS', 'false'),
        },
        'domain_counts': domain_counts,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def platform_metrics_summary(request):
    return Response({
        'service': 'agriasset-backend',
        'request_id': getattr(request, 'request_id', None),
        'metrics': platform_metrics.snapshot(),
    })


def render_prometheus_metrics() -> str:
    snapshot = platform_metrics.snapshot()
    outbox = persistent_outbox_snapshot()
    lines = [
        '# HELP agriasset_http_requests_total Total observed HTTP requests',
        '# TYPE agriasset_http_requests_total counter',
    ]
    for key, value in snapshot.get('requests', {}).items():
        method, _, path = key.partition(' ')
        lines.append(f'agriasset_http_requests_total{{method="{method}",path="{path}"}} {value}')
    lines.extend([
        '# HELP agriasset_http_status_total Total observed HTTP responses by status code',
        '# TYPE agriasset_http_status_total counter',
    ])
    for status, value in snapshot.get('status_codes', {}).items():
        lines.append(f'agriasset_http_status_total{{status="{status}"}} {value}')
    lines.extend([
        '# HELP agriasset_http_average_response_ms Average response time in milliseconds',
        '# TYPE agriasset_http_average_response_ms gauge',
    ])
    for key, value in snapshot.get('average_response_ms', {}).items():
        method, _, path = key.partition(' ')
        lines.append(f'agriasset_http_average_response_ms{{method="{method}",path="{path}"}} {value}')
    lines.extend([
        '# HELP agriasset_outbox_events Number of persistent outbox events by status',
        '# TYPE agriasset_outbox_events gauge',
    ])
    for status, value in outbox.get('counts', {}).items():
        lines.append(f'agriasset_outbox_events{{status="{status}"}} {value}')
    lines.extend([
        '# HELP agriasset_outbox_locked_events Number of currently locked outbox events',
        '# TYPE agriasset_outbox_locked_events gauge',
        f'agriasset_outbox_locked_events {outbox.get("locked_count", 0)}',
        '# HELP agriasset_outbox_retry_ready_events Number of outbox events ready for retry',
        '# TYPE agriasset_outbox_retry_ready_events gauge',
        f'agriasset_outbox_retry_ready_events {outbox.get("retry_ready_count", 0)}',
        '# HELP agriasset_strict_farm_scope_headers Whether strict farm scope headers are enabled (1/0)',
        '# TYPE agriasset_strict_farm_scope_headers gauge',
        f'agriasset_strict_farm_scope_headers {1 if os.getenv("STRICT_FARM_SCOPE_HEADERS", "false").lower() in {"1", "true", "yes", "on"} else 0}',
    ])
    return '\n'.join(lines) + '\n'


@api_view(['GET'])
@permission_classes([AllowAny])
def prometheus_metrics(request):
    return HttpResponse(render_prometheus_metrics(), content_type='text/plain; version=0.0.4; charset=utf-8')


# ─────────────────────────────────────────────────────────────────────────────
# TI-11: Yemen Context Performance Middleware
# Adapted for weak-internet / field device context.
# Tracks slow requests locally and exposes them via Django logger.
# Does NOT require external APM (Sentry, Datadog, etc.) to function.
# ─────────────────────────────────────────────────────────────────────────────

import logging
import time

_perf_logger = logging.getLogger("smart_agri.core.performance")


class YemenContextPerformanceMiddleware:
    """
    TI-11: Yemen-context performance middleware.

    Adapted for weak-internet deployments where p95 ≤ 2s is the PRD V21 SLA,
    but field devices may have slower connectivity. Uses a 500ms threshold for
    slow-query detection on device-facing endpoints.

    Configuration:
        AGRIASSET_SLOW_REQUEST_THRESHOLD_MS  -- env var, default 500
        AGRIASSET_PERF_LOG_FARM_HEADER       -- header name for farm_id context (X-Farm-ID)

    Log format (structured, JSON-parsable):
        SLOW_REQUEST | method | path | elapsed_ms | farm_id | user
    """

    SLOW_THRESHOLD_MS: int = int(
        os.environ.get("AGRIASSET_SLOW_REQUEST_THRESHOLD_MS", "500")
    )
    FARM_HEADER: str = os.environ.get(
        "AGRIASSET_PERF_LOG_FARM_HEADER", "HTTP_X_FARM_ID"
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request._perf_start = time.monotonic()
        response = self.get_response(request)
        elapsed_ms = (time.monotonic() - request._perf_start) * 1000

        # Track all requests in platform metrics
        platform_metrics.record_request(
            method=request.method,
            path=request.path,
            status=response.status_code,
            elapsed_ms=elapsed_ms,
        )

        if elapsed_ms >= self.SLOW_THRESHOLD_MS:
            farm_id = (
                request.META.get(self.FARM_HEADER)
                or getattr(request, "farm_id", None)
                or "N/A"
            )
            user_id = (
                request.user.id
                if hasattr(request, "user") and request.user and request.user.is_authenticated
                else "anon"
            )
            _perf_logger.warning(
                "SLOW_REQUEST",
                extra={
                    "method": request.method,
                    "path": request.path,
                    "elapsed_ms": round(elapsed_ms, 2),
                    "status_code": response.status_code,
                    "farm_id": farm_id,
                    "user_id": user_id,
                    "threshold_ms": self.SLOW_THRESHOLD_MS,
                },
            )

        return response

