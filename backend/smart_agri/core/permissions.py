import logging

from rest_framework import permissions
from rest_framework.exceptions import ParseError, UnsupportedMediaType

from smart_agri.core.models.settings import FarmSettings
from smart_agri.core.services.mode_policy_service import (
    TRANSITIONAL_SIMPLE_DISPLAY_FLAGS_NOTE,
    transitional_simple_display_flags_snapshot,
)

logger = logging.getLogger(__name__)


def _coerce_farm_id(value):
    if value in (None, "", []):
        return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def resolve_request_farm_id(request, view=None):
    """Resolve farm scope for governed mutating requests without implicit fallback."""

    parser_context = getattr(request, "parser_context", {}) or {}
    kwargs = parser_context.get("kwargs", {}) or {}
    for candidate in (
        kwargs.get("farm_pk"),
        kwargs.get("farm_id"),
        kwargs.get("farm"),
    ):
        farm_id = _coerce_farm_id(candidate)
        if farm_id is not None:
            return farm_id

    try:
        data = request.data
    except (AttributeError, TypeError, ParseError, UnsupportedMediaType):
        data = {}
    if isinstance(data, dict):
        for candidate in (
            data.get("farm"),
            data.get("farm_id"),
            data.get("farmId"),
        ):
            farm_id = _coerce_farm_id(candidate)
            if farm_id is not None:
                return farm_id

    query_params = getattr(request, "query_params", {}) or {}
    for candidate in (
        query_params.get("farm"),
        query_params.get("farm_id"),
    ):
        farm_id = _coerce_farm_id(candidate)
        if farm_id is not None:
            return farm_id

    headers = getattr(request, "headers", {}) or {}
    for candidate in (
        headers.get("X-Farm-Id"),
        headers.get("X-Farm-ID"),
    ):
        farm_id = _coerce_farm_id(candidate)
        if farm_id is not None:
            return farm_id

    for candidate in (
        getattr(request, "resolved_farm_id", None),
        getattr(request, "farm_scope_hint", None),
    ):
        farm_id = _coerce_farm_id(candidate)
        if farm_id is not None:
            return farm_id

    if view is not None:
        detail_pk = _coerce_farm_id(kwargs.get("pk"))
        queryset = getattr(view, "queryset", None)
        model = getattr(queryset, "model", None)
        if detail_pk is not None and model is not None:
            if hasattr(model, "farm_id"):
                inferred = queryset.filter(pk=detail_pk).values_list("farm_id", flat=True).first()
                farm_id = _coerce_farm_id(inferred)
                if farm_id is not None:
                    return farm_id
            if hasattr(model, "request_id"):
                inferred = queryset.filter(pk=detail_pk).values_list("request__farm_id", flat=True).first()
                farm_id = _coerce_farm_id(inferred)
                if farm_id is not None:
                    return farm_id
            if hasattr(model, "fiscal_year_id"):
                inferred = queryset.filter(pk=detail_pk).values_list("fiscal_year__farm_id", flat=True).first()
                farm_id = _coerce_farm_id(inferred)
                if farm_id is not None:
                    return farm_id

    return None


class StrictModeRequired(permissions.BasePermission):
    """
    [AGRI-GUARDIAN Axis 4, 10]
    API Permissions Guard: Hard blocker for STRICT-only endpoints.
    Allows GET (read-only) in SIMPLE mode if user has access,
    but strictly blocks POST/PUT/PATCH/DELETE unless Farm is in STRICT mode.
    """

    message = "🔴 [FORENSIC BLOCK] This endpoint requires STRICT mode. Financial authoring in SIMPLE mode is strictly prohibited."

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True  # Read access is governed by RLS/Farm scope

        farm_id = resolve_request_farm_id(request, view=view)
        if farm_id is not None:
            request.resolved_farm_id = farm_id

        if farm_id is None:
            logger.warning("[StrictModeRequired] Missing farm_id in request. Denying modification.")
            return False

        try:
            settings = FarmSettings.objects.get(farm_id=farm_id)
            if settings.mode == FarmSettings.MODE_STRICT:
                return True

            transitional_flags = transitional_simple_display_flags_snapshot(settings)
            if any(transitional_flags.values()):
                logger.info(
                    "[StrictModeRequired] SIMPLE transitional flags remain %s. "
                    "farm=%s finance=%s stock=%s employees=%s",
                    TRANSITIONAL_SIMPLE_DISPLAY_FLAGS_NOTE,
                    farm_id,
                    transitional_flags["show_finance_in_simple"],
                    transitional_flags["show_stock_in_simple"],
                    transitional_flags["show_employees_in_simple"],
                )
            logger.warning(f"[StrictModeRequired] Farm {farm_id} is in SIMPLE mode. Blocking modification.")
            return False
        except FarmSettings.DoesNotExist:
            logger.warning(f"[StrictModeRequired] Settings for farm {farm_id} not found. Denying modification.")
            return False
