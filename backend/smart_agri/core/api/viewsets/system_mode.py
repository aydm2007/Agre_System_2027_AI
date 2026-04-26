"""
System Mode API - Per-farm effective mode resolver.

Returns the effective SIMPLE/STRICT mode for a resolved farm scope:
- ?farm=<id> query param
- X-Farm-Id header
- first accessible farm for authenticated user
- fallback SIMPLE when context is unavailable
"""

import logging
from django.core.exceptions import ValidationError
from django.db import OperationalError
from rest_framework import permissions, viewsets
from rest_framework.response import Response

from smart_agri.core.api.error_contract import build_error_payload, request_id_from_request
from smart_agri.core.api.permissions import _ensure_user_has_farm_access, user_farm_ids
from smart_agri.core.models.farm import Farm
from smart_agri.core.models.log import AuditLog
from smart_agri.core.models.settings import SystemSettings
from smart_agri.core.services.mode_policy_service import build_fallback_settings, build_mode_payload, resolve_farm_settings
from smart_agri.core.services.policy_engine_service import PolicyEngineService

logger = logging.getLogger(__name__)



class SystemModeViewSet(viewsets.ViewSet):
    """
    GET /api/v1/system-mode/

    Returns effective mode payload.
    """

    permission_classes = [permissions.AllowAny]

    def _pick_farm_id(self, request):
        farm_param = request.query_params.get("farm")
        farm_header = request.headers.get("X-Farm-Id")
        candidate = farm_param or farm_header
        if candidate:
            try:
                return int(candidate), "request"
            except (TypeError, ValueError):
                return None, "invalid_request"

        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return None, "no_context"

        farm_ids = user_farm_ids(user)
        if not farm_ids:
            return None, "no_membership"
        return int(farm_ids[0]), "default_membership"

    @staticmethod
    def _audit_fallback(request, reason, farm_id=None):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return
        try:
            AuditLog.objects.create(
                action="SYSTEM_MODE_FALLBACK",
                model="SystemMode",
                object_id=str(farm_id or 0),
                actor=user,
                new_payload={"reason": reason, "farm_id": farm_id},
                reason="Per-farm mode fallback to SIMPLE",
            )
        except (ValidationError, OperationalError, TypeError, ValueError) as exc:
            logger.warning(
                "system_mode_fallback_audit_failed event=SYSTEM_MODE_FALLBACK_AUDIT_FAILURE "
                "farm_id=%s user_id=%s reason=%s path=%s request_id=%s error=%s",
                farm_id,
                getattr(user, "id", None),
                reason,
                getattr(request, "path", ""),
                request_id_from_request(request),
                exc,
            )

    @staticmethod
    def _audit_divergence(request, *, farm_id, divergence):
        if not divergence.get("detected"):
            return
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return
        try:
            AuditLog.objects.create(
                action="SYSTEM_MODE_DIVERGENCE",
                model="FarmSettings",
                object_id=str(farm_id or 0),
                actor=user,
                new_payload=divergence,
                reason="Legacy global strict mode diverges from farm mode.",
            )
        except (ValidationError, OperationalError, TypeError, ValueError) as exc:
            logger.warning(
                "system_mode_divergence_audit_failed farm_id=%s user_id=%s request_id=%s error=%s",
                farm_id,
                getattr(user, "id", None),
                request_id_from_request(request),
                exc,
            )

    def list(self, request):
        global_settings = SystemSettings.get_settings()
        farm_id, source_hint = self._pick_farm_id(request)
        user = getattr(request, "user", None)

        if source_hint == "invalid_request":
            if user and user.is_authenticated:
                self._audit_fallback(request, "invalid_farm_context")
            return Response(
                build_mode_payload(
                    settings=build_fallback_settings(),
                    global_settings=global_settings,
                    source="fallback:invalid_farm_context",
                    farm_id=None,
                )
            )

        if farm_id is None:
            if user and user.is_authenticated:
                self._audit_fallback(request, source_hint)
            return Response(
                build_mode_payload(
                    settings=build_fallback_settings(),
                    global_settings=global_settings,
                    source=f"fallback:{source_hint}",
                    farm_id=None,
                )
            )

        farm = Farm.objects.filter(pk=farm_id, deleted_at__isnull=True).first()
        if farm is None:
            if user and user.is_authenticated:
                self._audit_fallback(request, "farm_not_found", farm_id=farm_id)
            return Response(
                build_mode_payload(
                    settings=build_fallback_settings(),
                    global_settings=global_settings,
                    source="fallback:farm_not_found",
                    farm_id=farm_id,
                )
            )

        if user and user.is_authenticated:
            _ensure_user_has_farm_access(user, farm.id)

        settings, source, resolved_farm_id = resolve_farm_settings(farm=farm)
        if source != "farm_settings" and user and user.is_authenticated:
            self._audit_fallback(request, source.replace("fallback:", ""), farm_id=farm.id)
        extra = None
        if source == "fallback:farm_settings_table_missing":
            extra = build_error_payload(
                "تعذر تحميل إعدادات المزرعة، تم تطبيق الوضع المبسط افتراضيا.",
                request=request,
                code="FARM_SETTINGS_FALLBACK",
            )

        divergence = PolicyEngineService.policy_divergence(settings_obj=settings, global_settings=global_settings)
        if user and user.is_authenticated:
            self._audit_divergence(request, farm_id=farm.id, divergence=divergence)

        return Response(
            build_mode_payload(
                settings=settings,
                global_settings=global_settings,
                source=source,
                farm_id=resolved_farm_id,
                extra=extra,
            )
        )
