from __future__ import annotations

import logging
import time
from uuid import uuid4

from django.db import DatabaseError, OperationalError

from smart_agri.core.models.settings import FarmSettings


logger = logging.getLogger(__name__)


class RequestObservabilityMiddleware:
    """Attach request ID and processing time headers for easier tracing."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = time.perf_counter()
        request_id = (
            request.headers.get('X-Request-Id')
            or request.headers.get('X-Request-ID')
            or str(uuid4())
        )
        correlation_id = (
            request.headers.get('X-Correlation-Id')
            or request.headers.get('X-Correlation-ID')
            or request.headers.get('X-Idempotency-Key')
            or request.headers.get('Idempotency-Key')
            or request_id
        )
        request.request_id = request_id
        request.correlation_id = correlation_id
        response = self.get_response(request)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response['X-Request-Id'] = request_id
        response['X-Correlation-Id'] = correlation_id
        response['X-Response-Time-Ms'] = str(duration_ms)
        farm_scope = self._farm_id_for_request(request)
        policy_farm_id = self._policy_lookup_farm_id(farm_scope)
        effective_mode, approval_profile = self._policy_metadata(farm_id=policy_farm_id)
        route_name = getattr(getattr(request, 'resolver_match', None), 'view_name', '') or request.path
        user = getattr(request, 'user', None)
        logger.info(
            'request.completed',
            extra={
                'request_id': request_id,
                'correlation_id': correlation_id,
                'method': request.method,
                'path': request.path,
                'route_name': route_name,
                'farm_id': farm_scope,
                'policy_farm_id': policy_farm_id,
                'user_id': getattr(user, 'id', None) if getattr(user, 'is_authenticated', False) else None,
                'effective_mode': effective_mode,
                'approval_profile': approval_profile,
                'status_code': getattr(response, 'status_code', None),
                'duration_ms': duration_ms,
            },
        )
        return response

    @staticmethod
    def _farm_id_for_request(request):
        for header_name in ('X-Farm-ID', 'X-Farm-Id'):
            value = request.headers.get(header_name)
            if value:
                return str(value)
        for param_name in ('farm_id', 'farm'):
            value = request.GET.get(param_name)
            if value:
                return str(value)
        profile = getattr(getattr(request, 'user', None), 'employee_profile', None)
        farm_id = getattr(profile, 'farm_id', None)
        return str(farm_id) if farm_id else None

    @staticmethod
    def _policy_lookup_farm_id(farm_scope):
        if not farm_scope:
            return None
        normalized = str(farm_scope).strip()
        if not normalized or ',' in normalized:
            return None
        try:
            return str(int(normalized))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _policy_metadata(*, farm_id):
        if not farm_id:
            return None, None
        try:
            settings_obj = FarmSettings.objects.filter(farm_id=farm_id).only('mode', 'approval_profile').first()
        except (DatabaseError, OperationalError):
            return None, None
        if not settings_obj:
            return None, None
        return getattr(settings_obj, 'mode', None), getattr(settings_obj, 'approval_profile', None)
