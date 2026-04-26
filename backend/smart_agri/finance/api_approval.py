"""
[AGRI-GUARDIAN] Approval Rules & Requests API
Extracted from finance/api.py for maintainability.
"""
from django.db import transaction
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from smart_agri.core.api.viewsets.base import AuditedModelViewSet
from smart_agri.core.permissions import StrictModeRequired
from smart_agri.core.api.permissions import user_farm_ids
from smart_agri.core.services.ops_remediation_service import OpsRemediationService
from smart_agri.finance.models import ApprovalRule, ApprovalRequest, ApprovalStageEvent
from smart_agri.finance.services.approval_service import ApprovalGovernanceService




class ApprovalStageEventSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source='actor.username', read_only=True)
    role_label = serializers.SerializerMethodField()

    class Meta:
        model = ApprovalStageEvent
        fields = [
            'id', 'stage_number', 'role', 'role_label', 'action_type', 'actor', 'actor_username', 'note', 'created_at',
        ]
        read_only_fields = fields

    def get_role_label(self, obj):
        return ApprovalGovernanceService.ROLE_LABELS.get(obj.role, obj.role)


class ApprovalRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalRule
        fields = [
            'id', 'farm', 'module', 'action', 'cost_center', 'min_amount', 'max_amount',
            'required_role', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class ApprovalRequestSerializer(serializers.ModelSerializer):
    requester_name = serializers.CharField(source='requested_by.username', read_only=True)
    approver_name = serializers.CharField(source='approved_by.username', read_only=True)
    cost_center_name = serializers.CharField(source='cost_center.name', read_only=True)
    amount = serializers.DecimalField(source='requested_amount', max_digits=19, decimal_places=4, read_only=True)
    queue_snapshot = serializers.SerializerMethodField()
    stage_chain = serializers.SerializerMethodField()
    can_current_user_approve = serializers.SerializerMethodField()
    stage_events = serializers.SerializerMethodField()
    workflow_blueprint = serializers.SerializerMethodField()
    can_current_user_override = serializers.SerializerMethodField()
    can_current_user_reopen = serializers.SerializerMethodField()

    class Meta:
        model = ApprovalRequest
        fields = [
            'id', 'farm', 'module', 'action', 'cost_center', 'cost_center_name', 'content_type', 'object_id',
            'requested_amount', 'amount', 'status', 'required_role', 'final_required_role', 'current_stage',
            'total_stages', 'approval_history', 'requested_by', 'requester_name', 'approved_by', 'approver_name',
            'approved_at', 'rejection_reason', 'queue_snapshot', 'stage_chain', 'can_current_user_approve', 'can_current_user_override', 'can_current_user_reopen', 'stage_events', 'workflow_blueprint',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'required_role', 'final_required_role', 'current_stage', 'total_stages', 'approval_history',
            'requested_by', 'approved_by', 'approved_at', 'created_at', 'updated_at', 'queue_snapshot', 'stage_chain',
            'can_current_user_approve', 'can_current_user_override', 'can_current_user_reopen', 'stage_events', 'workflow_blueprint', 'amount', 'requester_name', 'approver_name', 'cost_center_name',
        ]

    def get_queue_snapshot(self, obj):
        return ApprovalGovernanceService.queue_snapshot(req=obj)

    def get_stage_chain(self, obj):
        return self.get_queue_snapshot(obj).get('stage_chain', [])

    def get_stage_events(self, obj):
        return ApprovalGovernanceService.stage_events_payload(req=obj)

    def get_can_current_user_approve(self, obj):
        request = self.context.get('request')
        if not request or not getattr(request, 'user', None):
            return False
        return ApprovalGovernanceService.can_approve(request.user, obj)

    def get_can_current_user_override(self, obj):
        request = self.context.get('request')
        if not request or not getattr(request, 'user', None):
            return False
        return ApprovalGovernanceService.can_override_stage(request.user, obj)

    def get_can_current_user_reopen(self, obj):
        request = self.context.get('request')
        if not request or not getattr(request, 'user', None):
            return False
        return obj.status == ApprovalRequest.STATUS_REJECTED and (
            obj.requested_by_id == getattr(request.user, 'id', None)
            or ApprovalGovernanceService.can_override_stage(request.user, obj)
        )

    def get_workflow_blueprint(self, obj):
        return ApprovalGovernanceService.workflow_blueprint_for_request(req=obj)


class ApprovalRuleViewSet(AuditedModelViewSet):
    """@idempotent"""
    serializer_class = ApprovalRuleSerializer
    permission_classes = [IsAuthenticated, StrictModeRequired]
    enforce_idempotency = True

    def get_queryset(self):
        user = self.request.user
        qs = ApprovalRule.objects.filter(deleted_at__isnull=True).order_by('farm_id', 'module', 'action', 'min_amount')
        if not user.is_superuser:
            allowed_farms = user_farm_ids(user)
            qs = qs.filter(farm_id__in=allowed_farms)
        farm_id = self.request.query_params.get('farm') or self.request.query_params.get('farm_id')
        if farm_id:
            qs = qs.filter(farm_id=farm_id)
        return qs

    def perform_create(self, serializer):
        serializer.instance = ApprovalGovernanceService.create_rule(user=self.request.user, **serializer.validated_data)

    def perform_update(self, serializer):
        serializer.instance = ApprovalGovernanceService.update_rule(user=self.request.user, instance=serializer.instance, **serializer.validated_data)


class ApprovalRequestViewSet(AuditedModelViewSet):
    """@idempotent"""
    serializer_class = ApprovalRequestSerializer
    http_method_names = ['get', 'post', 'head', 'options']
    permission_classes = [IsAuthenticated, StrictModeRequired]
    enforce_idempotency = True

    def get_queryset(self):
        user = self.request.user
        qs = ApprovalRequest.objects.filter(deleted_at__isnull=True).select_related('farm', 'requested_by', 'approved_by', 'cost_center').prefetch_related('stage_events__actor').order_by('-created_at')
        if not user.is_superuser:
            allowed_farms = user_farm_ids(user)
            qs = qs.filter(farm_id__in=allowed_farms)
        farm_param = self.request.query_params.get('farm') or self.request.query_params.get('farm_id')
        if farm_param:
            try:
                farm_ids = [int(f.strip()) for f in farm_param.split(',') if f.strip().isdigit()]
                if farm_ids:
                    qs = qs.filter(farm_id__in=farm_ids)
            except ValueError:
                pass
        return qs

    def perform_create(self, serializer):
        serializer.instance = ApprovalGovernanceService.create_request(user=self.request.user, **serializer.validated_data)

    @action(detail=False, methods=['get'], url_path='my-queue')
    def my_queue(self, request):
        ids = [row['request_id'] for row in ApprovalGovernanceService.work_queue_for_user(request.user)]
        queryset = self.get_queryset().filter(id__in=ids).order_by('-updated_at')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='queue-summary')
    def queue_summary(self, request):
        return Response(ApprovalGovernanceService.queue_summary_for_user(request.user))

    @action(detail=False, methods=['get'], url_path='maintenance-summary')
    def maintenance_summary(self, request):
        return Response(ApprovalGovernanceService.maintenance_summary())

    @action(detail=False, methods=['get'], url_path='runtime-governance')
    def runtime_governance(self, request):
        return Response(ApprovalGovernanceService.runtime_governance_snapshot())

    @action(detail=False, methods=['get'], url_path='runtime-governance/detail')
    def runtime_governance_detail(self, request):
        limit = request.query_params.get('limit') or 50
        try:
            limit_value = int(limit)
        except (TypeError, ValueError):
            raise serializers.ValidationError({'limit': 'invalid limit'})
        return Response(ApprovalGovernanceService.runtime_governance_detail_snapshot(limit=limit_value))

    @action(detail=False, methods=['get'], url_path='role-workbench')
    def role_workbench(self, request):
        payload = ApprovalGovernanceService.role_workbench_snapshot()
        farm_param = str(request.query_params.get('farm') or request.query_params.get('farm_id') or '').strip()
        role_param = str(request.query_params.get('role') or '').strip()
        owner_scope = str(request.query_params.get('owner_scope') or '').strip().lower()
        lane_health = str(request.query_params.get('lane_health') or '').strip().lower()
        director_only = str(request.query_params.get('director_attention') or '').strip().lower() in {'1', 'true', 'yes'}
        overdue_only = str(request.query_params.get('overdue_only') or '').strip().lower() in {'1', 'true', 'yes'}
        rows = list(payload.get('rows', []))
        if farm_param:
            rows = [row for row in rows if str(row.get('farm_id')) == farm_param]
        if role_param:
            rows = [row for row in rows if row.get('role') == role_param]
        if owner_scope:
            rows = [row for row in rows if str(row.get('owner_scope') or '').lower() == owner_scope]
        if director_only:
            rows = [row for row in rows if row.get('director_attention')]
        if overdue_only:
            rows = [row for row in rows if row.get('overdue')]
        if lane_health:
            rows = [row for row in rows if str(row.get('lane_health') or '').lower() == lane_health]
        payload['rows'] = rows
        payload['filtered_count'] = len(rows)
        return Response(payload)

    @action(detail=False, methods=['get'], url_path='role-workbench-summary')
    def role_workbench_summary(self, request):
        return Response(ApprovalGovernanceService.workbench_summary())

    @action(detail=False, methods=['get'], url_path='attention-feed')
    def attention_feed(self, request):
        payload = ApprovalGovernanceService.attention_feed()
        farm_param = str(request.query_params.get('farm') or request.query_params.get('farm_id') or '').strip()
        severity = str(request.query_params.get('severity') or '').strip().lower()
        kind = str(request.query_params.get('kind') or '').strip().lower()
        items = list(payload.get('items', []))
        if farm_param:
            items = [item for item in items if str(item.get('farm_id') or '') == farm_param]
        if severity:
            items = [item for item in items if str(item.get('severity') or '').lower() == severity]
        if kind:
            items = [item for item in items if str(item.get('kind') or '').lower() == kind]
        payload['items'] = items
        payload['count'] = len(items)
        return Response(payload)

    @action(detail=False, methods=['get'], url_path='sector-dashboard')
    def sector_dashboard(self, request):
        return Response(ApprovalGovernanceService.sector_dashboard_snapshot())

    @action(detail=False, methods=['get'], url_path='policy-impact')
    def policy_impact(self, request):
        return Response(ApprovalGovernanceService.policy_impact_snapshot())

    @action(detail=False, methods=['get'], url_path='farm-governance')
    def farm_governance(self, request):
        farm_param = request.query_params.get('farm') or request.query_params.get('farm_id')
        if not farm_param:
            raise serializers.ValidationError({'farm': 'farm query param is required.'})
        try:
            farm_id = int(farm_param)
        except (TypeError, ValueError):
            raise serializers.ValidationError({'farm': 'invalid farm id.'})
        return Response(ApprovalGovernanceService.farm_governance_snapshot(farm_id=farm_id))

    @action(detail=False, methods=['get'], url_path='farm-ops')
    def farm_ops(self, request):
        farm_param = request.query_params.get('farm') or request.query_params.get('farm_id')
        if not farm_param:
            raise serializers.ValidationError({'farm': 'farm query param is required.'})
        try:
            farm_id = int(farm_param)
        except (TypeError, ValueError):
            raise serializers.ValidationError({'farm': 'invalid farm id.'})
        return Response(ApprovalGovernanceService.farm_ops_snapshot(farm_id=farm_id))

    @action(detail=False, methods=['get'], url_path='request-trace')
    def request_trace(self, request):
        request_param = request.query_params.get('request_id')
        correlation_id = request.query_params.get('correlation_id')
        if not request_param and not correlation_id:
            raise serializers.ValidationError({'detail': 'request_id or correlation_id is required.'})
        request_id = None
        if request_param:
            try:
                request_id = int(request_param)
            except (TypeError, ValueError):
                raise serializers.ValidationError({'request_id': 'invalid request id.'})
        payload = ApprovalGovernanceService.request_trace(
            request_id=request_id,
            correlation_id=correlation_id,
        )
        traced_request_id = payload.get('request', {}).get('id')
        if traced_request_id and not self.get_queryset().filter(pk=traced_request_id).exists():
            raise serializers.ValidationError({'detail': 'request trace is خارج نطاق المستخدم الحالي.'})
        return Response(payload)

    @action(detail=False, methods=['post'], url_path='runtime-governance/dry-run-maintenance')
    def runtime_governance_dry_run_maintenance(self, request):
        key, error_response = self._enforce_action_idempotency(request)
        if error_response is not None:
            return error_response
        payload = OpsRemediationService.dry_run_governance_maintenance(
            user=request.user,
            request_id=getattr(request, 'request_id', None),
            correlation_id=getattr(request, 'correlation_id', None),
        )
        response = Response(payload)
        self._commit_action_idempotency(request, key, object_id=str(payload.get('action_id') or ''), response=response)
        return response

    @action(detail=True, methods=['get'], url_path='timeline')
    def timeline(self, request, pk=None):
        req = self.get_queryset().get(pk=pk)
        serializer = ApprovalStageEventSerializer(req.stage_events.select_related('actor').all(), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        key, error_response = self._enforce_action_idempotency(request)
        if error_response is not None:
            return error_response
        with transaction.atomic():
            req = ApprovalGovernanceService.approve_request(user=request.user, request_id=int(pk), note=str(request.data.get('reason') or '').strip())
            response = Response({
                'status': req.status.lower(),
                'status_ar': 'تم الاعتماد النهائي' if req.status == 'APPROVED' else 'تم تمرير المرحلة',
                'current_stage': req.current_stage,
                'total_stages': req.total_stages,
                'required_role': req.required_role,
                'final_required_role': req.final_required_role,
            })
            self._commit_action_idempotency(request, key, object_id=str(req.id), response=response)
            return response

    @action(detail=True, methods=['post'], url_path='override-stage')
    def override_stage(self, request, pk=None):
        key, error_response = self._enforce_action_idempotency(request)
        if error_response is not None:
            return error_response
        with transaction.atomic():
            reason = str(request.data.get('reason') or '').strip()
            req = ApprovalGovernanceService.override_request(user=request.user, request_id=int(pk), reason=reason)
            response = Response({
                'status': req.status.lower(),
                'status_ar': 'تم override المرحـلة الحالية وفق سلطة قطاعية نهائية',
                'current_stage': req.current_stage,
                'total_stages': req.total_stages,
                'required_role': req.required_role,
                'final_required_role': req.final_required_role,
            })
            self._commit_action_idempotency(request, key, object_id=str(req.id), response=response)
            return response

    @action(detail=True, methods=['post'], url_path='reopen')
    def reopen(self, request, pk=None):
        key, error_response = self._enforce_action_idempotency(request)
        if error_response is not None:
            return error_response
        with transaction.atomic():
            reason = str(request.data.get('reason') or '').strip()
            req = ApprovalGovernanceService.reopen_request(user=request.user, request_id=int(pk), reason=reason)
            response = Response({
                'status': req.status.lower(),
                'status_ar': 'تمت إعادة فتح الطلب إلى بداية السلسلة',
                'current_stage': req.current_stage,
                'total_stages': req.total_stages,
                'required_role': req.required_role,
                'final_required_role': req.final_required_role,
            })
            self._commit_action_idempotency(request, key, object_id=str(req.id), response=response)
            return response

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        key, error_response = self._enforce_action_idempotency(request)
        if error_response is not None:
            return error_response
        with transaction.atomic():
            reason = str(request.data.get('reason') or '').strip()
            req = ApprovalGovernanceService.reject_request(user=request.user, request_id=int(pk), reason=reason)
            response = Response({'status': 'rejected', 'status_ar': 'تم الرفض'})
            self._commit_action_idempotency(request, key, object_id=str(req.id), response=response)
            return response
