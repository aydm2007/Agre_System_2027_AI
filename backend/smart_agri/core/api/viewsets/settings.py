"""
Settings/Core ViewSets
"""

import logging
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import OperationalError, ProgrammingError
from django.db.models import Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from smart_agri.core.api.error_contract import build_error_payload, request_id_from_request
from smart_agri.core.api.permissions import (
    FarmScopedPermission,
    _ensure_user_has_farm_access,
    _limit_queryset_to_user_farms,
    user_farm_ids,
)
from smart_agri.core.api.serializers import (
    CostConfigurationSerializer,
    FarmSettingsSerializer,
    SeasonSerializer,
    SupervisorSerializer,
    UnitConversionSerializer,
    UnitSerializer,
)
from smart_agri.core.models import Season, Supervisor, Unit, UnitConversion
from smart_agri.core.models.settings import FarmSettings, SystemSettings
from smart_agri.core.services.mode_policy_service import simple_policy_fallback_payload
from smart_agri.core.services.policy_engine_service import PolicyEngineService
from smart_agri.finance.models import CostConfiguration

from .base import AuditedModelViewSet

logger = logging.getLogger(__name__)


def _simple_policy_fallback(farm_id):
    return simple_policy_fallback_payload(farm_id)


class SeasonViewSet(AuditedModelViewSet):
    serializer_class = SeasonSerializer
    queryset = Season.objects.filter(is_active=True).order_by("-start_date")
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["name"]
    filterset_fields = ["is_active"]

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class UnitViewSet(AuditedModelViewSet):
    queryset = Unit.objects.filter(deleted_at__isnull=True).order_by("category", "name")
    serializer_class = UnitSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        category = self.request.query_params.get("category") if hasattr(self.request, "query_params") else None
        if category:
            qs = qs.filter(category=category)
        search = self.request.query_params.get("q") if hasattr(self.request, "query_params") else None
        if search:
            qs = qs.filter(
                Q(name__icontains=search) | Q(code__icontains=search) | Q(symbol__icontains=search)
            )
        return qs


class UnitConversionViewSet(AuditedModelViewSet):
    queryset = UnitConversion.objects.filter(deleted_at__isnull=True).select_related("from_unit", "to_unit")
    serializer_class = UnitConversionSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        unit_id = self.request.query_params.get("unit") if hasattr(self.request, "query_params") else None
        if unit_id:
            qs = qs.filter(Q(from_unit_id=unit_id) | Q(to_unit_id=unit_id))
        return qs

    def perform_create(self, serializer):
        instance = serializer.save()
        if not UnitConversion.objects.filter(
            from_unit=instance.to_unit,
            to_unit=instance.from_unit,
            deleted_at__isnull=True,
        ).exists():
            try:
                UnitConversion.objects.create(
                    from_unit=instance.to_unit,
                    to_unit=instance.from_unit,
                    multiplier=Decimal("1.0") / instance.multiplier,
                )
            except (ValidationError, OperationalError, ValueError) as exc:
                logger.warning("UnitConversion reciprocal create failed: %s", exc)
        return instance

    def perform_update(self, serializer):
        instance = serializer.save()
        try:
            reciprocal = UnitConversion.objects.filter(
                from_unit=instance.to_unit,
                to_unit=instance.from_unit,
                deleted_at__isnull=True,
            ).first()
            if reciprocal:
                reciprocal.multiplier = Decimal("1.0") / instance.multiplier
                reciprocal.save()
        except (ValidationError, OperationalError, ValueError) as exc:
            logger.warning("UnitConversion reciprocal update failed: %s", exc)
        return instance


class CostConfigurationViewSet(AuditedModelViewSet):
    queryset = CostConfiguration.objects.select_related("farm").filter(deleted_at__isnull=True)
    serializer_class = CostConfigurationSerializer
    permission_classes = [FarmScopedPermission]
    filterset_fields = ["farm"]

    def get_queryset(self):
        qs = super().get_queryset()
        return _limit_queryset_to_user_farms(qs, self.request.user, "farm_id__in")


class SupervisorViewSet(AuditedModelViewSet):
    serializer_class = SupervisorSerializer

    def get_queryset(self):
        ids = user_farm_ids(self.request.user)
        qs = Supervisor.objects.all().filter(deleted_at__isnull=True)
        return qs.filter(farm_id__in=ids) if not self.request.user.is_superuser else qs


class FarmSettingsViewSet(viewsets.ModelViewSet):
    """
    API for retrieving or patching FarmSettings.
    Only allows GET and PATCH.
    """

    queryset = FarmSettings.objects.select_related("farm").all()
    serializer_class = FarmSettingsSerializer
    permission_classes = [FarmScopedPermission]
    filterset_fields = ["farm"]
    http_method_names = ["get", "patch", "post"]

    def get_queryset(self):
        qs = super().get_queryset()
        return _limit_queryset_to_user_farms(qs, self.request.user, "farm_id__in")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["global_settings"] = SystemSettings.get_settings()
        return context

    def perform_update(self, serializer):
        instance = serializer.instance
        old_strict = instance.mode == FarmSettings.MODE_STRICT if instance else False
        new_mode = serializer.validated_data.get(
            "mode",
            instance.mode if instance else FarmSettings.MODE_SIMPLE,
        )
        new_strict = new_mode == FarmSettings.MODE_STRICT

        updated = serializer.save()

        if not old_strict and new_strict:
            from smart_agri.core.services.quarantine_service import ModeSwitchQuarantineService

            count = ModeSwitchQuarantineService.quarantine_pending_logs_on_mode_switch(
                farm=updated.farm,
                switched_by=self.request.user,
            )
            if count > 0:
                logger.info(
                    "Mode switch SIMPLE->STRICT: Quarantined %d logs for farm %s",
                    count,
                    updated.farm_id,
                )

        return updated

    def list(self, request, *args, **kwargs):
        farm_param = request.query_params.get("farm") or request.query_params.get("farm_id")
        if farm_param:
            try:
                farm_id = int(farm_param)
            except (TypeError, ValueError):
                return Response(
                    build_error_payload(
                        "Invalid farm id.",
                        request=request,
                        code="INVALID_FARM_ID",
                    ),
                    status=400,
                )
            _ensure_user_has_farm_access(request.user, farm_id)
        else:
            farm_ids = user_farm_ids(request.user)
            if not farm_ids:
                return Response({"results": []})
            farm_id = int(farm_ids[0])

        try:
            settings_obj, _ = FarmSettings.objects.get_or_create(farm_id=farm_id)
        except (ProgrammingError, OperationalError):
            logger.warning(
                "farm_settings_fallback event=FARM_SETTINGS_TABLE_MISSING farm_id=%s user_id=%s path=%s request_id=%s",
                farm_id,
                getattr(request.user, "id", None),
                getattr(request, "path", ""),
                request_id_from_request(request),
            )
            fallback_payload = _simple_policy_fallback(farm_id)
            fallback_payload.update(
                build_error_payload(
                    "تعذر تحميل جدول إعدادات المزرعة، تم تطبيق الوضع المبسط.",
                    request=request,
                    code="FARM_SETTINGS_FALLBACK",
                )
            )
            return Response({"results": [fallback_payload]})
        serializer = self.get_serializer(settings_obj)
        return Response({"results": [serializer.data]})

    @action(detail=True, methods=["get"], url_path="effective-policy")
    def effective_policy(self, request, pk=None):
        settings_obj = self.get_object()
        summary = PolicyEngineService.effective_policy_summary_for_farm(
            farm=settings_obj.farm,
            settings_obj=settings_obj,
        )
        return Response(summary)

    @action(detail=True, methods=["post"], url_path="policy-diff")
    def policy_diff(self, request, pk=None):
        settings_obj = self.get_object()
        patch_payload = request.data or {}
        diff = PolicyEngineService.diff_against_farm_settings_patch(
            farm=settings_obj.farm,
            patch_payload=patch_payload,
            settings_obj=settings_obj,
        )
        return Response(diff, status=status.HTTP_200_OK)
