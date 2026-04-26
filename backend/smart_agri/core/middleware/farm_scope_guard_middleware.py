from __future__ import annotations

import os

from django.http import JsonResponse

from smart_agri.core.permissions import _coerce_farm_id


class FarmScopeGuardMiddleware:
    """Optional strict farm-scope enforcement for mutating API requests.

    Disabled by default. When enabled, authenticated mutating /api/ requests must provide
    X-Farm-Id or a farm query/body hint so downstream code can enforce a clear tenant scope.
    """

    SAFE_METHODS = {'GET', 'HEAD', 'OPTIONS'}

    def __init__(self, get_response):
        self.get_response = get_response
        self.strict_enabled = os.getenv('STRICT_FARM_SCOPE_HEADERS', 'false').strip().lower() in {'1', 'true', 'yes', 'on'}

    def __call__(self, request):
        farm_header = request.headers.get('X-Farm-Id') or request.headers.get('X-Farm-ID')
        farm_hint = farm_header or request.GET.get('farm') or request.GET.get('farm_id')
        setattr(request, 'farm_scope_hint', farm_hint)
        resolved_farm_id = _coerce_farm_id(farm_hint)
        if resolved_farm_id is not None:
            setattr(request, 'resolved_farm_id', resolved_farm_id)

        requires_scope = (
            self.strict_enabled
            and request.path.startswith('/api/')
            and request.method not in self.SAFE_METHODS
            and getattr(request, 'user', None) is not None
            and getattr(request.user, 'is_authenticated', False)
            and not getattr(request.user, 'is_superuser', False)
        )
        if requires_scope and not farm_hint:
            return JsonResponse({
                'detail': 'Farm scope header required for mutating API requests.',
                'required_header': 'X-Farm-Id',
            }, status=400)
        response = self.get_response(request)
        if farm_hint:
            response['X-Farm-Scope'] = str(farm_hint)
        return response
