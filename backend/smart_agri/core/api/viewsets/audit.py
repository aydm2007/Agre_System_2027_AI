"""
[AGRI-GUARDIAN §6] Centralized Audit Dashboard API.
Provides read-only forensic access to append-only AuditLog.
"""
import logging
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import OperationalError
from rest_framework import serializers, viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django_filters import rest_framework as filters
from smart_agri.core.models.log import AuditLog
from smart_agri.core.api.error_contract import build_error_payload, request_id_from_request
from smart_agri.core.api.permissions import user_has_sector_finance_authority

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def log_ui_breach(request):
    """
    [AGRI-GUARDIAN Axis 12] Strict Route Auditing
    Logs an implicit AuditLog when a SIMPLE mode user attempts to access a STRICT financial URL.
    """
    target_url = request.data.get('target_url', 'unknown')
    raw_farm = request.data.get('farm_id') or request.headers.get('X-Farm-Id') or request.query_params.get('farm')
    try:
        farm_id = int(raw_farm) if raw_farm is not None else None
    except (TypeError, ValueError):
        farm_id = None
    try:
        AuditLog.objects.create(
            actor=request.user,
            action="ROUTE_BREACH_ATTEMPT",
            model="FrontendRouter",
            object_id=target_url,
            new_payload={
                "timestamp": request.data.get('timestamp'),
                "userAgent": request.META.get('HTTP_USER_AGENT'),
                "path": target_url,
                "mode": "SIMPLE",
                "farm_id": farm_id,
            },
            reason="Unauthorized attempt to access restricted financial route in SIMPLE mode."
        )
        return Response({"status": "logged"}, status=status.HTTP_201_CREATED)
    except (DjangoValidationError, OperationalError, TypeError, ValueError) as exc:
        logger.exception(
            "ui_route_breach_log_failed event=UI_ROUTE_BREACH_LOG_FAILED user_id=%s farm_id=%s path=%s request_id=%s",
            getattr(request.user, "id", None),
            farm_id,
            target_url,
            request_id_from_request(request),
        )
        return Response(
            build_error_payload(
                "تعذر تسجيل محاولة اختراق المسار.",
                request=request,
                code="AUDIT_BREACH_LOG_FAILURE",
                error=str(exc),
            ),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for the immutable AuditLog."""
    actor_name = serializers.CharField(source='actor.username', read_only=True, allow_null=True)
    
    class Meta:
        model = AuditLog
        fields = [
            'id', 'timestamp', 'actor', 'actor_name', 'action', 
            'model', 'object_id', 'new_payload', 'reason'
        ]
        read_only_fields = fields  # All fields are read-only


class AuditLogFilter(filters.FilterSet):
    """Filters for querying the AuditLog."""
    model = filters.CharFilter(field_name='model')
    action = filters.CharFilter(field_name='action')
    actor = filters.NumberFilter(field_name='actor_id')
    object_id = filters.CharFilter(field_name='object_id')
    timestamp__gte = filters.DateTimeFilter(field_name='timestamp', lookup_expr='gte')
    timestamp__lte = filters.DateTimeFilter(field_name='timestamp', lookup_expr='lte')
    # [Axis 6] Tenant isolation: filter by farm_id stored in new_payload JSON
    farm_id = filters.NumberFilter(method='filter_by_farm_id')

    class Meta:
        model = AuditLog
        fields = ['model', 'action', 'actor', 'object_id', 'timestamp__gte', 'timestamp__lte', 'farm_id']

    def filter_by_farm_id(self, queryset, name, value):
        """Filter audit logs by farm_id stored in the new_payload JSON field."""
        if value:
            return queryset.filter(new_payload__farm_id=value)
        return queryset


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    [AGRI-GUARDIAN §6] Centralized Audit Dashboard API.
    Provides read-only access to all forensic audit logs.
    Restricted to Superusers and Headquarters Finance Authority.

    [Axis 6] Farm scope is enforced via the farm_id filter parameter.
    HQ users (superuser/finance authority) may see cross-farm data for oversight.
    """
    queryset = AuditLog.objects.select_related('actor').order_by('-timestamp')
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = AuditLogFilter

    def get_queryset(self):
        user = self.request.user
        if not user.is_superuser and not user_has_sector_finance_authority(user):
            raise PermissionDenied("الوصول لسجل التدقيق مقصور على الإدارة العامة والرقابة.")
        
        return super().get_queryset()
