from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, F
from decimal import Decimal
from smart_agri.core.models import (
    Farm, Employee, EmploymentContract, CropPlan, 
    ItemInventory
)
from smart_agri.finance.models import FinancialLedger
from smart_agri.core.api.permissions import IsFarmManager
from smart_agri.core.services.ops_alert_service import OpsAlertService
from smart_agri.core.services.ops_health_service import OpsHealthService
from smart_agri.core.services.ops_remediation_service import OpsRemediationService

class DashboardViewSet(viewsets.ViewSet):
    """
    [Visibility Engine]
    Provides high-level aggregated data for Farm Managers.
    """
    permission_classes = [IsAuthenticated] # & IsFarmManager ideal

    @action(detail=False, methods=['get'])
    def payroll_summary(self, request):
        """
        HR Snapshot: Headcount & Burn Rate.
        """
        farm_id = request.query_params.get('farm_id')
        if not farm_id:
            return Response({'error': 'farm_id required'}, status=400)

        # 1. Headcount
        employees = Employee.objects.filter(farm_id=farm_id, is_active=True)
        headcount = employees.count()
        
        # 2. Monthly Liability (Burn Rate)
        # Sum of basic + allowances for all active contracts
        contracts = EmploymentContract.objects.filter(
            employee__farm_id=farm_id,
            is_active=True
        )
        burn_rate = Decimal(0)
        for c in contracts:
            burn_rate += (
                c.basic_salary + 
                c.housing_allowance + 
                c.transport_allowance + 
                c.other_allowance
            )
            
        return Response({
            'headcount': headcount,
            'monthly_burn_rate': burn_rate,
            'currency': 'YER'  # Default Yemeni Riyal
        })

    @action(detail=False, methods=['get'])
    def farm_summary(self, request):
        farm_id = request.query_params.get("farm_id")
        if not farm_id:
            profile = getattr(request.user, "employee_profile", None)
            if not profile:
                return Response({"error": "farm_id required"}, status=400)
            farm_id = profile.farm_id

        employees = Employee.objects.filter(farm_id=farm_id, is_active=True)
        headcount = employees.count()

        burn_rate = Decimal("0")
        contracts = EmploymentContract.objects.filter(employee__farm_id=farm_id, is_active=True)
        for contract in contracts:
            burn_rate += (
                contract.basic_salary
                + contract.housing_allowance
                + contract.transport_allowance
                + contract.other_allowance
            )

        active_plans = CropPlan.objects.filter(
            farm_id=farm_id,
            status="active",
            deleted_at__isnull=True,
        ).count()

        total_stock_value = Decimal("0")
        inventories = ItemInventory.objects.filter(
            farm_id=farm_id,
            deleted_at__isnull=True,
        ).select_related("item")
        for inv in inventories:
            unit_price = getattr(inv.item, "unit_price", Decimal("0")) or Decimal("0")
            total_stock_value += (inv.qty or Decimal("0")) * unit_price

        return Response({
            "headcount": headcount,
            "monthly_burn_rate": burn_rate,
            "active_plans": active_plans,
            "total_stock_value": total_stock_value,
        })

    @action(detail=False, methods=['get'], url_path='release-health')
    def release_health(self, request):
        return Response(OpsHealthService.release_health_snapshot())

    @action(detail=False, methods=['get'], url_path='release-health/detail')
    def release_health_detail(self, request):
        return Response(OpsHealthService.release_health_detail_snapshot())

    @action(detail=False, methods=['get'], url_path='aggregated-health')
    def aggregated_health(self, request):
        return Response({
            "release": OpsHealthService.release_health_snapshot(),
            "outbox": OpsHealthService.integration_outbox_health_snapshot(),
            "attachment": OpsHealthService.attachment_runtime_health_snapshot(),
        })

    @action(detail=False, methods=['get'], url_path='outbox-health')
    def outbox_health(self, request):
        return Response(OpsHealthService.integration_outbox_health_snapshot())

    @action(detail=False, methods=['get'], url_path='outbox-health/detail')
    def outbox_health_detail(self, request):
        farm_param = request.query_params.get('farm_id') or request.query_params.get('farm')
        limit = request.query_params.get('limit') or 50
        try:
            farm_id = int(farm_param) if farm_param not in (None, '', 'all') else None
            limit_value = int(limit)
        except (TypeError, ValueError):
            raise serializers.ValidationError({'detail': 'invalid outbox detail filters'})
        return Response(
            OpsHealthService.integration_outbox_detail_snapshot(
                status_filter=request.query_params.get('status') or None,
                event_type=request.query_params.get('event_type') or None,
                farm_id=farm_id,
                metadata_flag=request.query_params.get('metadata_flag') or None,
                limit=limit_value,
            )
        )

    @action(detail=False, methods=['post'], url_path='outbox-health/retry')
    def outbox_health_retry(self, request):
        payload = OpsRemediationService.retry_outbox_events(
            user=request.user,
            event_ids=request.data.get('event_ids') or [],
            request_id=getattr(request, 'request_id', None),
            correlation_id=getattr(request, 'correlation_id', None),
        )
        return Response(payload, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='attachment-runtime-health')
    def attachment_runtime_health(self, request):
        return Response(OpsHealthService.attachment_runtime_health_snapshot())

    @action(detail=False, methods=['get'], url_path='attachment-runtime-health/detail')
    def attachment_runtime_health_detail(self, request):
        farm_param = request.query_params.get('farm_id') or request.query_params.get('farm')
        limit = request.query_params.get('limit') or 50
        try:
            farm_id = int(farm_param) if farm_param not in (None, '', 'all') else None
            limit_value = int(limit)
        except (TypeError, ValueError):
            raise serializers.ValidationError({'detail': 'invalid attachment runtime filters'})
        return Response(
            OpsHealthService.attachment_runtime_detail_snapshot(
                farm_id=farm_id,
                risk_reason=request.query_params.get('risk_reason') or None,
                limit=limit_value,
            )
        )

    @action(detail=False, methods=['post'], url_path='attachment-runtime-health/rescan')
    def attachment_runtime_health_rescan(self, request):
        payload = OpsRemediationService.rescan_attachments(
            user=request.user,
            attachment_ids=request.data.get('attachment_ids') or [],
            request_id=getattr(request, 'request_id', None),
            correlation_id=getattr(request, 'correlation_id', None),
        )
        return Response(payload, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='ops-alerts')
    def ops_alerts(self, request):
        farm_param = request.query_params.get('farm') or request.query_params.get('farm_id')
        try:
            farm_id = int(farm_param) if farm_param not in (None, '', 'all') else None
        except (TypeError, ValueError):
            raise serializers.ValidationError({'farm': 'invalid farm id'})
        include_acknowledged = str(request.query_params.get('include_acknowledged') or '').lower() in {'1', 'true', 'yes'}
        limit = request.query_params.get('limit') or 25
        try:
            limit_value = int(limit)
        except (TypeError, ValueError):
            raise serializers.ValidationError({'limit': 'invalid limit'})
        return Response(
            OpsAlertService.alerts_snapshot(
                user=request.user,
                farm_id=farm_id,
                include_acknowledged=include_acknowledged,
                limit=limit_value,
            )
        )

    @action(detail=False, methods=['post'], url_path='ops-alerts/acknowledge')
    def acknowledge_ops_alert(self, request):
        payload = OpsAlertService.acknowledge_alert(
            user=request.user,
            fingerprint=request.data.get('fingerprint'),
            note=request.data.get('note') or '',
            request_id=getattr(request, 'request_id', None),
            correlation_id=getattr(request, 'correlation_id', None),
        )
        return Response(payload, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='ops-alerts/snooze')
    def snooze_ops_alert(self, request):
        payload = OpsAlertService.snooze_alert(
            user=request.user,
            fingerprint=request.data.get('fingerprint'),
            hours=request.data.get('hours'),
            note=request.data.get('note') or '',
            request_id=getattr(request, 'request_id', None),
            correlation_id=getattr(request, 'correlation_id', None),
        )
        return Response(payload, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='outbox-health/trace')
    def outbox_health_trace(self, request):
        payload = OpsAlertService.outbox_trace(
            user=request.user,
            event_id=request.query_params.get('event_id'),
            correlation_id=request.query_params.get('correlation_id'),
            request_id=getattr(request, 'request_id', None),
        )
        return Response(payload)

    @action(detail=False, methods=['get'], url_path='attachment-runtime-health/trace')
    def attachment_runtime_health_trace(self, request):
        attachment_id = request.query_params.get('attachment_id')
        if not attachment_id:
            raise serializers.ValidationError({'attachment_id': 'attachment_id is required'})
        payload = OpsAlertService.attachment_trace(
            user=request.user,
            attachment_id=attachment_id,
            request_id=getattr(request, 'request_id', None),
            correlation_id=getattr(request, 'correlation_id', None),
        )
        return Response(payload)

    @action(detail=False, methods=['get'], url_path='offline-ops')
    def offline_ops(self, request):
        farm_param = request.query_params.get('farm') or request.query_params.get('farm_id')
        try:
            farm_id = int(farm_param) if farm_param not in (None, '', 'all') else None
        except (TypeError, ValueError):
            raise serializers.ValidationError({'farm': 'invalid farm id'})
        return Response(OpsAlertService.offline_ops_snapshot(farm_id=farm_id))
