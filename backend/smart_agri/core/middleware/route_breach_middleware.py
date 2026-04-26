"""
Route Breach Audit Middleware
=============================
[AGRI-GUARDIAN Axis 7+15 / AGENTS.md §14]

Intercepts unauthorized attempts to access finance and governed mutation
surfaces in SIMPLE mode. The middleware never grants authoring bypass from
transitional SIMPLE visibility flags; it only logs visibility state and then
returns 403 with an AuditLog record.
"""

import logging
import os
import json
from unittest.mock import Mock

from django.db import DatabaseError, IntegrityError
from django.http import JsonResponse
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from smart_agri.core.models.log import AuditLog
from smart_agri.core.models.settings import FarmSettings
from smart_agri.core.services.mode_policy_service import (
    TRANSITIONAL_SIMPLE_DISPLAY_FLAGS_NOTE,
    transitional_simple_display_flags_snapshot,
)

logger = logging.getLogger(__name__)

FINANCIAL_URL_PREFIXES = (
    "/api/v1/finance/",
    "/api/v1/treasury/",
    "/api/v1/ledger/",
    "/api/v1/expenses/",
    "/api/v1/fiscal/",
)

GOVERNED_MUTATION_PREFIXES = (
    "/api/v1/sharecropping-contracts/",
    "/api/v1/fuel-reconciliation/",
    "/api/v1/petty-cash/",
    "/api/v1/supplier-settlement/",
    "/api/v1/fixed-assets/",
    "/api/v1/advances/",
    "/api/v1/approval/",
)

SAFE_PREFIXES = (
    "/api/health/",
    "/api/auth/",
    "/api/docs/",
    "/api/schema/",
    "/api/v1/finance/cost-centers/",
    "/api/v1/finance/approval-rules/",
    "/api/v1/finance/approval-requests/runtime-governance",
    "/api/v1/finance/approval-requests/farm-governance",
    "/api/v1/finance/approval-requests/farm-ops",
    "/api/v1/finance/approval-requests/sector-dashboard",
    "/api/v1/finance/approval-requests/role-workbench",
    "/api/v1/finance/approval-requests/attention-feed",
    "/api/v1/finance/approval-requests/queue-summary",
)

STRICT_PAYLOAD_KEYS = {
    "financial_trace",
    "strict_finance_trace",
    "ledger_metrics",
    "treasury_trace",
    "depreciation_trace",
    "contract_erp_details",
    "governed_approval_chain",
    "settlement_details",
    "exact_amount",
}

def _strip_strict_payloads(data):
    if isinstance(data, dict):
        return {
            k: _strip_strict_payloads(v)
            for k, v in data.items()
            if k not in STRICT_PAYLOAD_KEYS
        }
    elif isinstance(data, list):
        return [_strip_strict_payloads(item) for item in data]
    return data



def _farm_settings_model():
    if isinstance(FarmSettings, Mock):
        return FarmSettings
    from smart_agri.core.models.settings import FarmSettings as live_model

    return live_model


def _audit_log_model():
    if isinstance(AuditLog, Mock):
        return AuditLog
    from smart_agri.core.models.log import AuditLog as live_model

    return live_model


def _emergency_bypass_enabled(request, user) -> bool:
    if not getattr(user, "is_superuser", False):
        return False
    if os.getenv("AGRIASSET_EMERGENCY_STRICT_BYPASS", "").lower() not in {"1", "true", "yes"}:
        return False
    return request.headers.get("X-AgriAsset-Emergency-Bypass") == "1"


class RouteBreachAuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                try:
                    from rest_framework_simplejwt.authentication import JWTAuthentication

                    jwt_auth = JWTAuthentication()
                    validated_token = jwt_auth.get_validated_token(auth_header.split(" ")[1])
                    user = jwt_auth.get_user(validated_token)
                    request.user = user
                except (AuthenticationFailed, InvalidToken, TokenError, ValueError):
                    pass

        if not user or not getattr(user, "is_authenticated", False):
            return self.get_response(request)

        path = request.path_info
        targets_finance_surface = any(path.startswith(prefix) for prefix in FINANCIAL_URL_PREFIXES)
        targets_governed_mutation = request.method not in {"GET", "HEAD", "OPTIONS"} and any(
            path.startswith(prefix) for prefix in GOVERNED_MUTATION_PREFIXES
        )
        if not (targets_finance_surface or targets_governed_mutation):
            response = self.get_response(request)
            farm_id = _resolve_farm_id(request, request.user)
            if farm_id is not None:
                try:
                    farm_settings_model = _farm_settings_model()
                    farm_settings = farm_settings_model.objects.filter(farm_id=farm_id).first()
                    is_strict_mode = bool(farm_settings and farm_settings.mode == farm_settings_model.MODE_STRICT)
                except (AttributeError, LookupError):
                    is_strict_mode = False
            else:
                is_strict_mode = False

            if not is_strict_mode and getattr(response, "status_code", 200) == 200 and response.get("Content-Type", "").startswith("application/json"):
                is_governed_read = request.method in {"GET", "HEAD", "OPTIONS"} and any(
                    path.startswith(prefix) for prefix in GOVERNED_MUTATION_PREFIXES
                )
                if is_governed_read:
                    try:
                        payload = json.loads(response.content.decode("utf-8"))
                        cleaned = _strip_strict_payloads(payload)
                        response.content = json.dumps(cleaned).encode("utf-8")
                    except (TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
                        pass
            return response

        if any(path.startswith(prefix) for prefix in SAFE_PREFIXES):
            return self.get_response(request)

        farm_id = _resolve_farm_id(request, request.user)
        is_strict_mode = False
        farm_settings = None
        if farm_id is not None:
            try:
                farm_settings_model = _farm_settings_model()
                farm_settings = farm_settings_model.objects.filter(farm_id=farm_id).first()
                is_strict_mode = bool(
                    farm_settings and farm_settings.mode == farm_settings_model.MODE_STRICT
                )
            except (AttributeError, LookupError):
                is_strict_mode = False

        if is_strict_mode:
            return self.get_response(request)

        if farm_settings and (targets_finance_surface or targets_governed_mutation):
            transitional_flags = transitional_simple_display_flags_snapshot(farm_settings)
            if any(transitional_flags.values()):
                logger.info(
                    "[RouteBreachAuditMiddleware] SIMPLE transitional flags remain %s. "
                    "farm=%s path=%s finance=%s stock=%s employees=%s",
                    TRANSITIONAL_SIMPLE_DISPLAY_FLAGS_NOTE,
                    farm_id,
                    path,
                    transitional_flags["show_finance_in_simple"],
                    transitional_flags["show_stock_in_simple"],
                    transitional_flags["show_employees_in_simple"],
                )

        user = request.user
        if _emergency_bypass_enabled(request, user):
            logger.warning("Emergency STRICT bypass granted for user=%s path=%s", user.username, path)
            return self.get_response(request)

        try:
            _audit_log_model().objects.create(
                action="ROUTE_BREACH_ATTEMPT",
                model="RouteAccess",
                object_id="0",
                actor=user,
                new_payload={
                    "path": path,
                    "method": request.method,
                    "user_id": user.id,
                    "username": user.username,
                    "ip_address": _get_client_ip(request),
                    "system_mode": "SIMPLE",
                    "breach_surface": "finance" if targets_finance_surface else "governed_mutation",
                    "farm_id": farm_id,
                },
            )
            logger.warning("ROUTE BREACH: user=%s attempted access to %s in SIMPLE mode", user.username, path)
        except (DatabaseError, IntegrityError, ValueError, TypeError) as exc:
            logger.critical(
                "CRITICAL: Failed to log route breach for user=%s path=%s: %s",
                user.username,
                path,
                exc,
            )
            raise

        return self._breach_response()

    @staticmethod
    def _breach_response():
        return JsonResponse(
            {
                "detail": "غير مصرح بالوصول. هذا المسار متاح فقط في الوضع الصارم (ERP).",
                "code": "ROUTE_BREACH_SIMPLE_MODE",
            },
            status=403,
            json_dumps_params={"ensure_ascii": False},
        )


def _get_client_ip(request) -> str:
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def _resolve_farm_id(request, user):
    query_farm = request.GET.get("farm") or request.GET.get("farm_id")
    header_farm = request.headers.get("X-Farm-Id") or request.headers.get("X-Farm-ID")
    candidate = query_farm or header_farm
    if candidate:
        try:
            return int(candidate)
        except (TypeError, ValueError):
            return None
    try:
        from smart_agri.accounts.models import FarmMembership

        user_id = getattr(user, "id", None)
        if not isinstance(user_id, int):
            return None
        return (
            FarmMembership.objects.filter(user_id=user_id)
            .order_by("farm_id")
            .values_list("farm_id", flat=True)
            .first()
        )
    except (AttributeError, LookupError):
        return None
