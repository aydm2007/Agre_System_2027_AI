"""
[AGRI-GUARDIAN] Fiscal Year / Period API
Extracted from finance/api.py for maintainability.
"""
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from smart_agri.core.permissions import StrictModeRequired
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError as DRFValidationError

from smart_agri.core.api.viewsets.base import AuditedModelViewSet
from smart_agri.core.api.permissions import (
    user_farm_ids,
    _ensure_user_has_farm_access,
    user_has_farm_role,
    user_has_sector_finance_authority,
)
from smart_agri.core.throttles import FinancialMutationThrottle
from smart_agri.finance.models import FiscalYear, FiscalPeriod, ActualExpense
from smart_agri.finance.models_treasury import TreasuryTransaction
from smart_agri.finance.services.fiscal_rollover_service import FiscalYearRolloverService
from smart_agri.finance.services.fiscal_governance_service import FiscalGovernanceService
from smart_agri.core.models.log import DailyLog
from smart_agri.inventory.models import ItemInventory


# ─── Serializers ─────────────────────────────────────────────────────────────

class FiscalYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = FiscalYear
        fields = ['id', 'farm', 'year', 'start_date', 'end_date', 'is_closed']


class FiscalPeriodSerializer(serializers.ModelSerializer):
    fiscal_year_display = serializers.CharField(source='fiscal_year.year', read_only=True)

    class Meta:
        model = FiscalPeriod
        fields = [
            'id', 'fiscal_year', 'fiscal_year_display', 'month',
            'start_date', 'end_date', 'status', 'is_closed', 'closed_at', 'closed_by'
        ]


# ─── ViewSets ────────────────────────────────────────────────────────────────

class FiscalYearViewSet(AuditedModelViewSet):
    """
    سنة مالية (Fiscal Year).
    يجب أن تغطي فترة محددة ولا تتداخل مع سنوات أخرى لنفس المزرعة.
    @idempotent
    """
    serializer_class = FiscalYearSerializer
    queryset = FiscalYear.objects.filter(deleted_at__isnull=True)
    permission_classes = [IsAuthenticated, StrictModeRequired]
    throttle_classes = [FinancialMutationThrottle]
    # [AGRI-GUARDIAN] Weak-network doctrine: mutation retries must be safe.
    enforce_idempotency = True

    def get_queryset(self):
        user = self.request.user
        qs = FiscalYear.objects.filter(deleted_at__isnull=True).order_by('-year')

        if not user.is_superuser:
            allowed_farms = user_farm_ids(user)
            qs = qs.filter(farm_id__in=allowed_farms)

        farm_id = self.request.query_params.get('farm') or self.request.query_params.get('farm_id')
        if farm_id:
            qs = qs.filter(farm_id=farm_id)

        return qs

    @action(detail=True, methods=['post'], url_path='rollover')
    def rollover(self, request, pk=None):
        # [AGRI-GUARDIAN] Financial mutation endpoint -> strict Idempotency V2
        key, error_response = self._enforce_action_idempotency(request)
        if error_response:
            return error_response

        if not request.user.is_superuser:
            raise PermissionDenied("يتطلب ترحيل السنة المالية صلاحية الإدارة العامة.")

        start_date = parse_date(request.data.get('start_date'))
        end_date = parse_date(request.data.get('end_date'))

        try:
            with transaction.atomic():
                next_year = FiscalYearRolloverService.rollover_year(
                    pk,
                    new_start_date=start_date,
                    new_end_date=end_date,
                    user=request.user,
                )
                serializer = self.get_serializer(next_year)
                response = Response(serializer.data, status=status.HTTP_201_CREATED)
                self._commit_action_idempotency(
                    request,
                    key,
                    object_id=str(next_year.id),
                    response=response,
                )
                return response
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.message_dict if hasattr(exc, 'message_dict') else exc.messages[0] if exc.messages else str(exc))


class FiscalPeriodViewSet(AuditedModelViewSet):
    """
    فترة مالية (غالبًا شهر).
    @idempotent
    """
    serializer_class = FiscalPeriodSerializer
    queryset = FiscalPeriod.objects.filter(deleted_at__isnull=True).select_related('fiscal_year')
    permission_classes = [IsAuthenticated, StrictModeRequired]
    throttle_classes = [FinancialMutationThrottle]
    enforce_idempotency = True

    # AGENTS.md Fiscal Lifecycle Doctrine:
    # mutations must only happen through explicit soft-close/hard-close actions.
    def create(self, request, *args, **kwargs):
        return Response(
            {"error": "إنشاء الفترات المالية مباشرةً غير مسموح. استخدم تهيئة السنة المالية/الترحيل."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def update(self, request, *args, **kwargs):
        return Response(
            {"error": "تعديل الفترة المالية مباشرةً غير مسموح. استخدم إجراءات الإقفال المبدئي/النهائي."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def partial_update(self, request, *args, **kwargs):
        return Response(
            {"error": "تعديل الفترة المالية مباشرةً غير مسموح. استخدم إجراءات الإقفال المبدئي/النهائي."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"error": "حذف الفترة المالية غير مسموح. أي تصحيح بعد الإقفال يتم عبر قيود عكسية في فترة مفتوحة."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def get_queryset(self):
        user = self.request.user
        qs = FiscalPeriod.objects.filter(deleted_at__isnull=True).select_related('fiscal_year')

        if not user.is_superuser:
            allowed_farms = user_farm_ids(user)
            qs = qs.filter(fiscal_year__farm_id__in=allowed_farms)

        farm_id = self.request.query_params.get('farm') or self.request.query_params.get('farm_id')
        if farm_id:
            qs = qs.filter(fiscal_year__farm_id=farm_id)

        # Optional filter by fiscal_year
        fy_id = self.request.query_params.get('fiscal_year')
        if fy_id:
            qs = qs.filter(fiscal_year_id=fy_id)

        return qs.order_by('fiscal_year__year', 'month')

    def _transition_period_status(self, request, period_id, target_status, message):
        key, error_response = self._enforce_action_idempotency(request)
        if error_response:
            return error_response

        with transaction.atomic():
            period = FiscalPeriod.objects.select_related("fiscal_year").get(pk=period_id)
            normalized_target = FiscalPeriod._normalize_status(target_status)
            self._enforce_close_permission(request, period, normalized_target)
            try:
                period = FiscalGovernanceService.transition_period(
                    period_id=int(period_id),
                    target_status=normalized_target,
                    user=request.user,
                )
            except DjangoValidationError as exc:
                return Response({'error': str(exc)}, status=400)
            response = Response({'status': message})
            self._commit_action_idempotency(request, key, object_id=str(period.id), response=response)

        return response

    def _enforce_close_permission(self, request, period, target_status):
        user = request.user
        if user.is_superuser:
            return

        farm_id = period.fiscal_year.farm_id

        if target_status == FiscalPeriod.STATUS_SOFT_CLOSE:
            if not user_has_farm_role(user, farm_id, {"Manager", "Admin"}):
                raise PermissionDenied("الإغلاق المبدئي يتطلب صلاحية مدير المزرعة.")
            return
        if target_status == FiscalPeriod.STATUS_HARD_CLOSE:
            if not user_has_sector_finance_authority(user):
                raise PermissionDenied("الإغلاق النهائي يتطلب صلاحية الإدارة العامة.")

    def _enforce_reopen_permission(self, request, period):
        user = request.user
        if user.is_superuser:
            return
        if not user_has_sector_finance_authority(user):
            raise PermissionDenied("إعادة فتح الفترة المالية تتطلب اعتماداً قطاعياً نهائياً.")

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Deprecated one-click close endpoint: explicit lifecycle only."""
        return Response(
            {'error': 'Direct close is disabled. Use soft-close then hard-close explicitly.'},
            status=400,
        )

    @action(detail=True, methods=['post'], url_path='soft-close')
    def soft_close(self, request, pk=None):
        """Soft-close a fiscal period (review state)."""
        return self._transition_period_status(
            request, pk, FiscalPeriod.STATUS_SOFT_CLOSE,
            'تم الإغلاق المبدئي للفترة'
        )

    @action(detail=True, methods=['post'], url_path='hard-close')
    def hard_close(self, request, pk=None):
        """Hard-close a fiscal period."""
        return self._transition_period_status(
            request, pk, FiscalPeriod.STATUS_HARD_CLOSE,
            'تم إغلاق الفترة نهائياً'
        )

    @action(detail=True, methods=['post'], url_path='reopen')
    def reopen(self, request, pk=None):
        key, error_response = self._enforce_action_idempotency(request)
        if error_response:
            return error_response

        with transaction.atomic():
            period = FiscalPeriod.objects.select_related("fiscal_year").get(pk=pk)
            self._enforce_reopen_permission(request, period)
            reason = str(request.data.get('reason') or '').strip()
            try:
                period = FiscalGovernanceService.reopen_period(
                    period_id=int(pk),
                    user=request.user,
                    reason=reason,
                )
            except DjangoValidationError as exc:
                return Response({'error': str(exc)}, status=400)

            response = Response(
                {
                    'status': 'تمت إعادة فتح الفترة المالية',
                    'period_id': period.id,
                    'period_status': period.status,
                }
            )
            self._commit_action_idempotency(request, key, object_id=str(period.id), response=response)
            return response

    @action(detail=False, methods=['get'], url_path='control-tower')
    def control_tower(self, request):
        farm_id = request.query_params.get('farm_id') or request.headers.get('X-Farm-Id')
        if not farm_id:
            return Response({'detail': 'farm_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            farm_id = int(farm_id)
        except (TypeError, ValueError):
            return Response({'detail': 'farm_id must be a valid integer.'}, status=status.HTTP_400_BAD_REQUEST)

        _ensure_user_has_farm_access(request.user, farm_id)
        today = timezone.localdate()

        critical_variances = DailyLog.objects.filter(
            farm_id=farm_id, log_date=today, variance_status='CRITICAL', deleted_at__isnull=True,
        ).count()
        pending_expenses = ActualExpense.objects.filter(
            farm_id=farm_id, is_allocated=False, deleted_at__isnull=True,
        ).count()
        treasury_today = TreasuryTransaction.objects.filter(
            cash_box__farm_id=farm_id, created_at__date=today,
        ).aggregate(total=Sum('amount'))
        inventory_positions = ItemInventory.objects.filter(
            farm_id=farm_id, deleted_at__isnull=True,
        ).count()

        return Response({
            'farm_id': farm_id,
            'business_date': str(today),
            'kpis': {
                'critical_variances_today': critical_variances,
                'pending_expenses': pending_expenses,
                'treasury_amount_today': str(treasury_today.get('total') or Decimal('0.0000')),
                'inventory_positions': inventory_positions,
            },
        })
