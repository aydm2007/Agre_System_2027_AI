"""
Idempotency Middleware
======================
[AGRI-GUARDIAN Axis 2 / AGENTS.md Rule#4]

Enforces X-Idempotency-Key header on all financial POST/PATCH mutations.
Uses the existing IdempotencyService (acquire-lock -> execute -> commit)
to provide Stripe-style cache-replay for duplicate requests.

Non-financial mutations and read-only requests pass through unaffected.
"""
import json
import logging

from django.db import DatabaseError
from django.http import JsonResponse
from rest_framework import status as drf_status

logger = logging.getLogger(__name__)

# URL prefixes that MUST carry X-Idempotency-Key on POST/PATCH/PUT/DELETE
FINANCIAL_MUTATION_PREFIXES = (
    "/api/v1/finance/",
    "/api/v1/treasury/",
    "/api/v1/petty-cash/",
    "/api/v1/supplier-settlement/",
    "/api/v1/sharecropping-contracts/",
    "/api/v1/fuel-reconciliation/",
    "/api/v1/fixed-assets/",
    "/api/v1/fiscal/",
    "/api/v1/ledger/",
    "/api/v1/expenses/",
    "/api/v1/advances/",
    "/api/v1/approval/",
    "/api/v1/core/daily-logs/",
    "/api/v1/core/offline-daily-log-replay/",
)

MUTATION_METHODS = {"POST", "PATCH", "PUT", "DELETE"}

SAFE_PREFIXES = (
    "/api/health/",
    "/api/auth/",
    "/api/docs/",
    "/api/schema/",
)

READ_ONLY_SUFFIXES = (
    "/dashboard/",
    "/summary/",
    "/report/",
    "/export/",
    "/snapshot/",
    "/workbench/",
    "/queue/",
)


class IdempotencyMiddleware:
    """
    Django middleware enforcing X-Idempotency-Key on financial mutations.

    Behavior:
    - GET/HEAD/OPTIONS: pass through (no idempotency needed)
    - POST/PATCH/PUT/DELETE on financial URLs without key: 400 error
    - POST/PATCH/PUT/DELETE on financial URLs with key:
        - New key: acquire lock, proceed, commit success/failure
        - Existing key (succeeded): replay cached response
        - Existing key (in progress): 409 conflict
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method not in MUTATION_METHODS:
            return self.get_response(request)

        path = request.path_info
        if any(path.startswith(prefix) for prefix in SAFE_PREFIXES):
            return self.get_response(request)

        is_financial = any(path.startswith(prefix) for prefix in FINANCIAL_MUTATION_PREFIXES)
        if not is_financial:
            return self.get_response(request)

        if any(path.rstrip("/").endswith(suffix.rstrip("/")) for suffix in READ_ONLY_SUFFIXES):
            return self.get_response(request)

        idempotency_key = (
            request.headers.get("X-Idempotency-Key")
            or request.headers.get("Idempotency-Key")
            or request.META.get("HTTP_X_IDEMPOTENCY_KEY")
        )

        if not idempotency_key:
            return JsonResponse(
                {
                    "detail": "مطلوب ترويسة X-Idempotency-Key لضمان عدم تكرار العملية المالية.",
                    "code": "IDEMPOTENCY_KEY_REQUIRED",
                },
                status=drf_status.HTTP_400_BAD_REQUEST,
                json_dumps_params={"ensure_ascii": False},
            )

        if not getattr(request, "user", None) or not request.user.is_authenticated:
            return self.get_response(request)

        try:
            from smart_agri.core.services.idempotency import (
                IdempotencyLocked,
                IdempotencyMismatch,
                IdempotencyService,
            )

            body = self._get_request_body(request)
            params = dict(request.GET.items()) if request.GET else {}
            farm_id = self._resolve_farm_id(request)

            record, is_replay, response_data = IdempotencyService.acquire_lock(
                key=idempotency_key,
                user=request.user,
                method=request.method,
                path=path,
                body=body,
                params=params,
                farm_id=farm_id,
            )

            if is_replay and response_data:
                status_code, body_data = response_data
                logger.info(
                    "Idempotency replay: key=%s user=%s path=%s",
                    idempotency_key,
                    request.user.username,
                    path,
                )
                return JsonResponse(
                    body_data if isinstance(body_data, dict) else {"data": body_data},
                    status=status_code or drf_status.HTTP_200_OK,
                    json_dumps_params={"ensure_ascii": False},
                )

            request._idempotency_record = record
            request._idempotency_key = idempotency_key
            response = self.get_response(request)

            try:
                if 200 <= response.status_code < 300:
                    response_body = self._extract_response_body(response)
                    IdempotencyService.commit_success(
                        record,
                        response_status=response.status_code,
                        response_body=response_body,
                    )
                elif response.status_code >= 400:
                    IdempotencyService.commit_failure(record)
            except (AttributeError, DatabaseError, TypeError, ValueError) as exc:
                logger.warning(
                    "Failed to commit idempotency status for key=%s: %s",
                    idempotency_key,
                    exc,
                )

            return response

        except IdempotencyLocked as exc:
            logger.warning(
                "Idempotency locked: key=%s user=%s path=%s",
                idempotency_key,
                request.user.username,
                path,
            )
            return JsonResponse(
                {"detail": str(exc.detail), "code": "IDEMPOTENCY_LOCKED"},
                status=drf_status.HTTP_409_CONFLICT,
                json_dumps_params={"ensure_ascii": False},
            )
        except IdempotencyMismatch as exc:
            logger.warning(
                "Idempotency mismatch: key=%s user=%s path=%s",
                idempotency_key,
                request.user.username,
                path,
            )
            return JsonResponse(
                {"detail": str(exc.detail), "code": "IDEMPOTENCY_MISMATCH"},
                status=drf_status.HTTP_409_CONFLICT,
                json_dumps_params={"ensure_ascii": False},
            )
        except (AttributeError, DatabaseError, ImportError, TypeError, ValueError):
            # If idempotency infra is unavailable, let the request through
            # (fail-open for availability, viewset-level check is backup)
            logger.exception("Idempotency middleware error for key=%s", idempotency_key)
            return self.get_response(request)

    @staticmethod
    def _get_request_body(request):
        """Safely extract request body as dict."""
        try:
            if hasattr(request, "data"):
                return request.data
            body_bytes = request.body
            if body_bytes:
                return json.loads(body_bytes)
        except (AttributeError, json.JSONDecodeError, ValueError):
            pass
        return {}

    @staticmethod
    def _resolve_farm_id(request):
        """Extract farm_id from request context."""
        candidate = (
            request.GET.get("farm")
            or request.GET.get("farm_id")
            or request.headers.get("X-Farm-Id")
            or request.headers.get("X-Farm-ID")
        )
        if candidate:
            try:
                return int(candidate)
            except (TypeError, ValueError):
                return None
        return None

    @staticmethod
    def _extract_response_body(response):
        """Safely extract response body for caching."""
        try:
            if hasattr(response, "data"):
                return response.data
            content = response.content
            if content:
                return json.loads(content)
        except (AttributeError, json.JSONDecodeError, ValueError):
            pass
        return {}
