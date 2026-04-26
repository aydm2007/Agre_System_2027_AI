"""
[AGRI-GUARDIAN] Actual Expense API — CRUD
Extracted from finance/api.py for maintainability.
"""
from decimal import Decimal

from django.db.models import Sum, Count, Q, DecimalField
from django_filters import rest_framework as filters
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from smart_agri.core.permissions import StrictModeRequired
from rest_framework.response import Response

from smart_agri.core.api.viewsets.base import AuditedModelViewSet
from smart_agri.core.api.permissions import user_farm_ids, _ensure_user_has_farm_access
from smart_agri.core.throttles import FinancialMutationThrottle
from smart_agri.finance.models import ActualExpense, CostCenter
from smart_agri.finance.services.actual_expense_service import ActualExpenseService
from smart_agri.finance.services.core_finance import FinanceService
from smart_agri.finance.services.cost_center_service import CostCenterService


# ─── Serializers ─────────────────────────────────────────────────────────────

class CostCenterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CostCenter
        fields = ['id', 'farm', 'code', 'name', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ActualExpenseSerializer(serializers.ModelSerializer):
    """Serializer for Actual Expenses (CRUD allowed)."""
    farm_name = serializers.CharField(source='farm.name', read_only=True)
    budget_classification_code = serializers.CharField(source='budget_classification.code', read_only=True)

    class Meta:
        model = ActualExpense
        fields = [
            'id', 'farm', 'farm_name', 'date', 'amount', 'description',
            'budget_classification', 'budget_classification_code', 'replenishment_reference',
            'account_code', 'currency', 'exchange_rate', 'amount_local',
            'is_allocated', 'allocated_at', 'period_start', 'period_end',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'amount_local', 'created_at', 'updated_at']

    def validate_amount(self, value):
        """Ensure amount is positive."""
        if value <= 0:
            raise serializers.ValidationError('المبلغ يجب أن يكون أكبر من صفر.')
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        instance = getattr(self, 'instance', None)
        budget_classification = attrs.get('budget_classification') or getattr(instance, 'budget_classification', None)
        replenishment_reference = attrs.get('replenishment_reference') or getattr(instance, 'replenishment_reference', None)

        if not budget_classification:
            raise serializers.ValidationError({'budget_classification': 'رمز بند الميزانية (BudgetCode) إلزامي لقيد المصروف.'})
        if not replenishment_reference:
            raise serializers.ValidationError({'replenishment_reference': 'مرجع التعزيز المعتمد إلزامي لقيد المصروف.'})
        return attrs


# ─── Filter ──────────────────────────────────────────────────────────────────

class ActualExpenseFilter(filters.FilterSet):
    """Filter for Actual Expenses."""
    farm = filters.NumberFilter(field_name='farm_id')
    date__gte = filters.DateFilter(field_name='date', lookup_expr='gte')
    date__lte = filters.DateFilter(field_name='date', lookup_expr='lte')
    is_allocated = filters.BooleanFilter(field_name='is_allocated')
    account_code = filters.CharFilter(field_name='account_code')

    class Meta:
        model = ActualExpense
        fields = ['farm', 'date__gte', 'date__lte', 'is_allocated', 'account_code']

    location = filters.NumberFilter(method='filter_location')
    crop_plan = filters.NumberFilter(method='filter_crop_plan')

    def filter_location(self, queryset, name, value):
        return queryset

    def filter_crop_plan(self, queryset, name, value):
        return queryset


# ─── ViewSets ────────────────────────────────────────────────────────────────

class ActualExpenseViewSet(AuditedModelViewSet):
    """
    [AGRI-GUARDIAN] Actual Expense API - Full CRUD

    Note: Unlike FinancialLedger, ActualExpense IS mutable.
    These are planning/budget expenses before they get allocated to Ledger.
    مصروف فعلي مباشر لا يمر بنظام المشتريات/الموردين.
    @idempotent
    """
    serializer_class = ActualExpenseSerializer
    enforce_idempotency = True
    permission_classes = [IsAuthenticated, StrictModeRequired]
    throttle_classes = [FinancialMutationThrottle]
    filterset_class = ActualExpenseFilter
    ordering = ['-date', '-id']

    def get_queryset(self):
        user = self.request.user
        qs = ActualExpense.objects.filter(deleted_at__isnull=True).select_related('farm')

        if not user.is_superuser:
            allowed_farms = user_farm_ids(user)
            qs = qs.filter(farm_id__in=allowed_farms)

        farm_id = self.request.query_params.get('farm')
        if farm_id:
            qs = qs.filter(farm_id=farm_id)

        return qs.order_by('-date', '-id')

    def perform_create(self, serializer):
        FinanceService.check_fiscal_period(
            serializer.validated_data.get("date"),
            serializer.validated_data.get("farm"),
            strict=True,
        )
        instance = ActualExpenseService.create_expense(
            user=self.request.user,
            **serializer.validated_data,
        )
        serializer.instance = instance
        self._log_action(
            "create",
            instance,
            payload=self.get_serializer(instance).data,
            reason=self.request.data.get("audit_reason", ""),
        )

    def perform_update(self, serializer):
        FinanceService.check_fiscal_period(
            serializer.validated_data.get("date", serializer.instance.date),
            serializer.validated_data.get("farm", serializer.instance.farm),
            strict=True,
        )
        old_data = self.get_serializer(serializer.instance).data
        instance = ActualExpenseService.update_expense(
            user=self.request.user,
            instance=serializer.instance,
            **serializer.validated_data,
        )
        serializer.instance = instance
        self._log_action(
            "update",
            instance,
            payload=self.get_serializer(instance).data,
            old_payload=old_data,
            reason=self.request.data.get("audit_reason", ""),
        )

    @action(detail=True, methods=['post'])
    def allocate(self, request, pk=None):
        """Mark expense as allocated (linked to cost allocation)."""
        key, error_response = self._enforce_action_idempotency(request)
        if error_response:
            return error_response

        expense = ActualExpenseService.allocate_expense(user=request.user, expense_id=int(pk))
        response = Response({'status': 'تم تخصيص المصروف بنجاح'})
        self._commit_action_idempotency(request, key, object_id=str(expense.id), response=response)
        return response

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get summary of expenses."""
        qs = self.filter_queryset(self.get_queryset())

        total = qs.aggregate(
            total_amount=Sum('amount', output_field=DecimalField()),
            total_local=Sum('amount_local', output_field=DecimalField()),
            allocated_count=Count('id', filter=Q(is_allocated=True)),
        )

        return Response({
            'total_amount': total['total_amount'] or 0,
            'total_local': total['total_local'] or 0,
            'total_count': qs.count(),
            'allocated_count': qs.filter(is_allocated=True).count(),
            'pending_count': qs.filter(is_allocated=False).count(),
        })


class CostCenterViewSet(AuditedModelViewSet):
    """
    [AGRI-GUARDIAN §Axis-2] ViewSet for CostCenter. Farm isolation is mandatory.
    @idempotent
    Cost Center mutations must be retry-safe (weak-network doctrine, Northern Yemen).
    """
    serializer_class = CostCenterSerializer
    filter_backends = [filters.DjangoFilterBackend]
    filterset_fields = ['farm', 'is_active', 'code']
    # [AGRI-GUARDIAN] Mutation retries must be safe (Axis-2 mandate)
    enforce_idempotency = True

    def get_queryset(self):
        user = self.request.user
        qs = CostCenter.objects.all()
        farm_ids = user_farm_ids(user)
        if not farm_ids:
            return qs.none()
        qs = qs.filter(farm__in=farm_ids)

        farm_id = self.request.query_params.get("farm_id")
        if farm_id:
            qs = qs.filter(farm_id=farm_id)

        return qs.order_by('code')

    def perform_create(self, serializer):
        from smart_agri.finance.services.cost_center_service import CostCenterService
        if not serializer.validated_data.get('farm') and hasattr(self.request, 'user'):
            pass # Or handle default farm logic
        
        instance = CostCenterService.create_cost_center(
            user=self.request.user,
            **serializer.validated_data,
        )
        serializer.instance = instance

    def perform_update(self, serializer):
        from smart_agri.finance.services.cost_center_service import CostCenterService
        instance = CostCenterService.update_cost_center(
            user=self.request.user,
            instance=self.get_object(),
            **serializer.validated_data,
        )
        serializer.instance = instance

    def perform_destroy(self, instance):
        instance.delete()
