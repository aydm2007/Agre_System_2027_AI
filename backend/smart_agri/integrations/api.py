from __future__ import annotations

import logging
from urllib.parse import urlparse

import requests
from rest_framework import permissions, routers, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from smart_agri.core.api.permissions import user_farm_ids
from smart_agri.core.api.viewsets.base import AuditedModelViewSet

from .models import ExternalFinanceBatch, ExternalFinanceLine, OutboundDelivery, WebhookEndpoint
from .services import ExternalFinanceBatchService

logger = logging.getLogger(__name__)


class WebhookEndpointSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookEndpoint
        fields = "__all__"

    def validate_target_url(self, value):
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https"):
            raise serializers.ValidationError("البروتوكول غير صالح. يجب استخدام http أو https.")
        hostname = parsed.hostname
        if not hostname:
            raise serializers.ValidationError("اسم المضيف غير صالح.")
        forbidden_hosts = ["localhost", "127.0.0.1", "::1", "0.0.0.0"]
        if hostname.lower() in forbidden_hosts:
            raise serializers.ValidationError("لا يمكن للخطافات استهداف المضيف المحلي (Localhost).")
        if hostname.startswith("192.168.") or hostname.startswith("10.") or hostname.startswith("172.16."):
            raise serializers.ValidationError("لا يمكن للخطافات استهداف الشبكات الخاصة.")
        return value


class OutboundDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = OutboundDelivery
        fields = "__all__"


class WebhookEndpointViewSet(AuditedModelViewSet):
    queryset = WebhookEndpoint.objects.all().order_by("-created_at")
    serializer_class = WebhookEndpointSerializer
    permission_classes = [permissions.IsAdminUser]


class OutboundDeliveryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = OutboundDelivery.objects.select_related("endpoint").all().order_by("-created_at")
    serializer_class = OutboundDeliverySerializer
    permission_classes = [permissions.IsAuthenticated]


class ExternalFinanceLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalFinanceLine
        fields = "__all__"


class ExternalFinanceBatchSerializer(serializers.ModelSerializer):
    lines = ExternalFinanceLineSerializer(many=True, read_only=True)

    class Meta:
        model = ExternalFinanceBatch
        fields = "__all__"


class ExternalFinanceBatchViewSet(AuditedModelViewSet):
    queryset = ExternalFinanceBatch.objects.select_related("farm", "exported_by").prefetch_related("lines").all().order_by("-created_at")
    serializer_class = ExternalFinanceBatchSerializer
    permission_classes = [permissions.IsAuthenticated]
    enforce_idempotency = True

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_superuser:
            qs = qs.filter(farm_id__in=user_farm_ids(user))
        farm_id = self.request.query_params.get("farm") or self.request.query_params.get("farm_id")
        if farm_id:
            qs = qs.filter(farm_id=farm_id)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        batch = ExternalFinanceBatchService.create_batch(user=request.user, validated_data=serializer.validated_data)
        output = self.get_serializer(batch)
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=201, headers=headers)

    @action(detail=True, methods=["post"], url_path="build-from-ledger")
    def build_from_ledger(self, request, pk=None):
        key, error_response = self._enforce_action_idempotency(request)
        if error_response is not None:
            return error_response
        result = ExternalFinanceBatchService.build_from_ledger(user=request.user, batch_id=int(pk))
        if result.status == ExternalFinanceBatch.STATUS_FAILED:
            response = Response(
                {
                    "detail": result.detail,
                    "total_debit": str(result.total_debit),
                    "total_credit": str(result.total_credit),
                },
                status=400,
            )
        else:
            response = Response({"status": result.status, "line_count": result.line_count})
        self._commit_action_idempotency(request, key, object_id=str(result.batch.id), response=response)
        return response

    @action(detail=True, methods=["post"], url_path="acknowledge")
    def acknowledge(self, request, pk=None):
        key, error_response = self._enforce_action_idempotency(request)
        if error_response is not None:
            return error_response
        external_ref = str(request.data.get("external_ref") or "").strip()
        if not external_ref:
            raise serializers.ValidationError({"external_ref": "external_ref is required"})
        try:
            result = ExternalFinanceBatchService.acknowledge_batch(user=request.user, batch_id=int(pk), external_ref=external_ref)
        except ValueError as exc:
            raise serializers.ValidationError({"external_ref": str(exc)}) from exc
        response = Response({"status": result.status, "external_ref": external_ref})
        self._commit_action_idempotency(request, key, object_id=str(result.batch.id), response=response)
        return response


router = routers.DefaultRouter()
router.register(r"integrations/webhooks", WebhookEndpointViewSet, basename="webhooks")
router.register(r"integrations/deliveries", OutboundDeliveryViewSet, basename="deliveries")
router.register(r"integrations/finance-batches", ExternalFinanceBatchViewSet, basename="finance-batches")


def fetch_weather_data(lat, lon):
    """Fetch weather without blocking core business flows."""
    try:
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": lat, "longitude": lon, "current_weather": True},
            timeout=5,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as exc:
        logger.warning("Weather API unreachable: %s. System continuing in Offline Mode.", exc)
        return {"current_weather": {"temperature": None, "weathercode": -1}}
