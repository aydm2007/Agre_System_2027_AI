"""
[AGRI-GUARDIAN] Financial Ledger API — Read-Only
Extracted from finance/api.py for maintainability.
"""
import logging
from decimal import Decimal
from decimal import InvalidOperation

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError
from django_filters import rest_framework as df_filters # Renamed alias to avoid conflict
from rest_framework import serializers, viewsets, status
from rest_framework import filters as rf_filters # Imported rest_framework filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from smart_agri.core.permissions import StrictModeRequired
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from smart_agri.core.api.viewsets.base import IdempotentCreateMixin
from smart_agri.core.api.permissions import (
    user_farm_ids,
    _ensure_user_has_farm_access,
    user_has_sector_finance_authority,
)
from smart_agri.finance.models import FinancialLedger
from smart_agri.finance.services.ledger_approval_service import LedgerApprovalService
from smart_agri.finance.api_ledger_support import (
    analytical_summary_for_queryset,
    accumulate_actual_materials,
    build_ledger_queryset_for_user,
    build_standard_bom,
    compute_material_variance_report,
    ensure_crop_plan_access,
    resolve_farm_action_context,
    summarize_ledger_queryset,
)

logger = logging.getLogger(__name__)


# ─── Serializer ──────────────────────────────────────────────────────────────

class FinancialLedgerSerializer(serializers.ModelSerializer):
    """Read-only serializer for Financial Ledger entries."""
    activity_name = serializers.CharField(source='activity.name', read_only=True, allow_null=True)
    cost_center_name = serializers.CharField(source='cost_center.name', read_only=True, allow_null=True)
    crop_plan_name = serializers.CharField(source='crop_plan.name', read_only=True, allow_null=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    account_code_name = serializers.SerializerMethodField()
    localized_description = serializers.SerializerMethodField()
    ACCOUNT_NAME_AR = {
        FinancialLedger.ACCOUNT_CASH_ON_HAND: 'نقد بالصندوق',
        FinancialLedger.ACCOUNT_BANK: 'بنك',
        FinancialLedger.ACCOUNT_PAYABLE_VENDOR: 'دائنون - موردين',
        FinancialLedger.ACCOUNT_EXPENSE_ADMIN: 'مصروفات إدارية / عهد',
        '1000-LABOR': 'تكلفة العمالة',
        '1200-RECEIVABLE': 'ذمم مدينة',
        '1300-INV-ASSET': 'أصول المخزون',
        '1400-WIP': 'أعمال تحت التنفيذ',
        '1500-ACC-DEP': 'الإهلاك المتراكم',
        '2000-MATERIAL': 'تكلفة المواد',
        '2000-PAY-SAL': 'رواتب مستحقة',
        '2100-SECTOR-PAY': 'حساب القطاع الإنتاجي',
        '3000-MACHINERY': 'تكلفة الآليات',
        '4000-OVERHEAD': 'نفقات عامة',
        '5000-REVENUE': 'إيرادات المبيعات',
        '6000-COGS': 'تكلفة البضاعة المباعة',
        '7000-DEP-EXP': 'مصروف الإهلاك',
        '7100-ZAKAT-EXP': 'مصروف الزكاة',
        '2200-ZAKAT-PAY': 'زكاة مستحقة',
        '9999-SUSPENSE': 'حساب معلق',
    }

    @staticmethod
    def _localize_legacy_description(description: str) -> str:
        if not description:
            return description

        # If already Arabic (or mixed Arabic) keep as-is.
        if any('\u0600' <= ch <= '\u06FF' for ch in description):
            return description

        text = str(description)
        replacements = [
            ("REVERSAL Sector Payable: Invoice #", "قيد عكسي لمستحقات حساب القطاع الإنتاجي - فاتورة رقم "),
            ("REVERSAL Sales Revenue: Invoice #", "قيد عكسي لإيراد المبيعات - فاتورة رقم "),
            ("REVERSAL Receivable: Invoice #", "قيد عكسي للذمم المدينة - فاتورة رقم "),
            ("Sector Payable: Invoice #", "مستحق تحويل لحساب القطاع الإنتاجي - فاتورة رقم "),
            ("Sales Revenue: Invoice #", "إثبات إيراد المبيعات - فاتورة رقم "),
            ("COGS Invoice #", "تكلفة البضاعة المباعة - فاتورة رقم "),
            ("Inv Reduction #", "تخفيض أصل المخزون - فاتورة رقم "),
            ("Invoice #", "فاتورة رقم "),
            (" (Inv #", " - فاتورة رقم "),
        ]
        for source, target in replacements:
            text = text.replace(source, target)

        text = text.replace("Sector Current Remittance", "تحويل مستحقات القطاع الإنتاجي")
        text = text.replace("Receivable:", "ذمم مدينة:")
        text = text.replace("Liability Adjustment:", "تسوية التزام:")
        text = text.replace("Activity Cost Adjustment:", "تسوية تكلفة نشاط:")
        text = text.replace("REVERSAL Adjustment:", "قيد عكسي لتسوية:")
        text = text.replace("DELETE REVERSAL:", "قيد عكسي للحذف:")
        text = text.replace("Solar Operational Depreciation:", "استهلاك تشغيلي للأصول الشمسية:")
        text = text.replace("Solar Reserve Accrual:", "تجنيب احتياطي الأصول الشمسية:")
        text = text.replace("REVERSAL Solar Operational Depreciation:", "قيد عكسي لاستهلاك الأصول الشمسية:")
        text = text.replace("REVERSAL Solar Reserve Accrual:", "قيد عكسي لتجنيب احتياطي الأصول الشمسية:")
        text = text.replace("REVERSAL (Deletion):", "قيد عكسي (حذف):")
        text = text.replace("REVERSAL", "قيد عكسي")

        # Close transformed "(Inv #...)" tail if present.
        if " - فاتورة رقم " in text:
            text = text.replace(")", "")

        return text

    def get_localized_description(self, obj):
        return self._localize_legacy_description(obj.description)

    def get_account_code_name(self, obj):
        return self.ACCOUNT_NAME_AR.get(obj.account_code, obj.account_code)

    class Meta:
        model = FinancialLedger
        fields = [
            'id', 'activity', 'activity_name', 'account_code',
            'account_code_name', 'debit', 'credit', 'description',
            'localized_description', 'currency', 'tax_amount',
            'cost_center', 'cost_center_name', 'crop_plan', 'crop_plan_name',
            'created_at', 'created_by', 'created_by_name',
            'approved_by', 'row_hash'
        ]
        read_only_fields = fields  # ALL fields are read-only


# ─── Filter ──────────────────────────────────────────────────────────────────

class LedgerFilter(df_filters.FilterSet): # Using df_filters alias
    account_code = df_filters.CharFilter(field_name='account_code')
    activity = df_filters.NumberFilter(field_name='activity_id')
    activity_id = df_filters.NumberFilter(field_name='activity_id')
    crop_plan = df_filters.NumberFilter(method='filter_crop_plan')
    crop_plan_id = df_filters.NumberFilter(method='filter_crop_plan')
    cost_center = df_filters.NumberFilter(method='filter_cost_center')
    cost_center_id = df_filters.NumberFilter(method='filter_cost_center')
    # Compare on date-part to keep end-date inclusive for DateTime fields.
    created_at__gte = df_filters.DateFilter(method='filter_created_at_gte')
    created_at__lte = df_filters.DateFilter(method='filter_created_at_lte')

    def filter_created_at_gte(self, queryset, name, value):
        return queryset.filter(created_at__date__gte=value)

    def filter_created_at_lte(self, queryset, name, value):
        return queryset.filter(created_at__date__lte=value)

    class Meta:
        model = FinancialLedger
        fields = [
            'account_code',
            'activity',
            'activity_id',
            'crop_plan',
            'crop_plan_id',
            'cost_center',
            'cost_center_id',
            'created_at__gte',
            'created_at__lte',
        ]

    # [AGRI-GUARDIAN] URL Filters
    location = df_filters.NumberFilter(method='filter_location')
    location_id = df_filters.NumberFilter(method='filter_location')

    def filter_location(self, queryset, name, value):
        return queryset.filter(
            Q(activity__activity_locations__location_id=value) |
            Q(crop_plan__plan_locations__location_id=value)
        ).distinct()

    def filter_crop_plan(self, queryset, name, value):
        return queryset.filter(
            Q(crop_plan_id=value) |
            Q(activity__crop_plan_id=value)
        ).distinct()

    def filter_cost_center(self, queryset, name, value):
        return queryset.filter(
            Q(cost_center_id=value) |
            Q(activity__cost_center_id=value)
        ).distinct()


# ─── ViewSet ─────────────────────────────────────────────────────────────────

class FinancialLedgerViewSet(IdempotentCreateMixin, viewsets.ReadOnlyModelViewSet):
    """
    [AGRI-GUARDIAN] Financial Ledger API - READ-ONLY

    Protocol II: Financial Immutability
    - No create, update, or delete operations allowed.
    - Modifications must go through Service Layer (reversal transactions).
    - [Security] Strict Tenant Isolation applied via 'activity__crop_plan__farm'.
    - [Offline Immunity] Any future write path MUST enforce X-Idempotency-Key.
    """
    http_method_names = ['get', 'head', 'options']
    serializer_class = FinancialLedgerSerializer
    permission_classes = [IsAuthenticated, StrictModeRequired]
    filter_backends = [
        rf_filters.SearchFilter,
        rf_filters.OrderingFilter,
        df_filters.DjangoFilterBackend,
    ] # Using rf_filters and df_filters
    filterset_class = LedgerFilter
    ordering = ['-created_at']
    ordering_fields = ['created_at', 'debit', 'credit', 'account_code', 'id']

    def get_queryset(self):
        return build_ledger_queryset_for_user(request=self.request, user=self.request.user)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Returns aggregated totals for the ledger."""
        qs = self.filter_queryset(self.get_queryset())
        return Response(summarize_ledger_queryset(qs))

    @action(detail=False, methods=['get'])
    def validate_balances(self, request):
        """
        [AGRI-GUARDIAN §3] Fiscal Lifecycle: Auto-Balancing Validation
        Validates the fundamental accounting equation: SUM(Debit) == SUM(Credit)
        Returns a 200 status if balanced, 400 with variance alert if imbalanced.
        """
        if not user_has_sector_finance_authority(request.user) and not request.user.is_superuser:
            raise PermissionDenied("إجراء الفحص المالي يتطلب صلاحية الإدارة العامة (المدير المالي).")

        farm_id = request.query_params.get('farm')
        fiscal_period_id = request.query_params.get('fiscal_period')

        if not farm_id:
            return Response(
                {'error': 'معامل farm مطلوب. لا يمكن تنفيذ استعلام عام بدون تحديد المزرعة (Axis 6).'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            farm_id = int(farm_id)
            if fiscal_period_id:
                fiscal_period_id = int(fiscal_period_id)
        except (TypeError, ValueError):
            return Response({'error': 'قيم farm أو fiscal_period غير صحيحة.'}, status=status.HTTP_400_BAD_REQUEST)

        from smart_agri.finance.services.ledger_balancing import LedgerBalancingService

        is_balanced = LedgerBalancingService.validate_balances(farm_id=farm_id, fiscal_period_id=fiscal_period_id)

        if is_balanced:
            return Response({'status': 'الميزان المالي مطابق (Debit == Credit) للقيود المحددة.'})

        return Response(
            {'error': 'تم اكتشاف خلل في التوازن المالي (القيود غير متطابقة). تم رفع إنذار للوحة التحكم.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=False, methods=['get'])
    def analytical_summary(self, request):
        """
        [AGRI-GUARDIAN] Analytical Accounting Report (Multi-Dimensional P&L).
        Groups financial ledger entries by analytical dimensions (Cost Center & Crop Plan).
        """
        qs = self.filter_queryset(self.get_queryset())
        return Response(analytical_summary_for_queryset(qs))

    @action(detail=False, methods=['post'], url_path='ias41-revalue')
    def ias41_revalue(self, request):
        """
        [AGRI-GUARDIAN §10] IAS 41 Biological Asset Revaluation.
        Accepts a farm_id and a valuation_map (cohort_id -> fair_value_per_unit).
        Posts paired journal entries for fair value gains/losses.
        @idempotent
        """
        if not user_has_sector_finance_authority(request.user) and not request.user.is_superuser:
            raise PermissionDenied("إعادة تقييم الأصول البيولوجية يتطلب صلاحية الإدارة العامة (المدير المالي).")

        farm_id = request.data.get('farm_id')
        valuation_map_raw = request.data.get('valuation_map', {})

        if not farm_id or not valuation_map_raw:
            error_response = Response(
                {'error': 'يجب تحديد farm_id و valuation_map (cohort_id → fair_value_per_unit).'},
                status=status.HTTP_400_BAD_REQUEST,
            )
            return error_response

        key, error_response = self._enforce_action_idempotency(request, farm_id=farm_id)
        if error_response:
            return error_response

        from smart_agri.core.models.farm import Farm
        try:
            farm = Farm.objects.get(pk=int(farm_id))
        except (Farm.DoesNotExist, ValueError, TypeError):
            error_response = Response({'error': 'المزرعة غير موجودة.'}, status=status.HTTP_404_NOT_FOUND)
            self._commit_action_idempotency(request, key, response=error_response)
            return error_response

        _ensure_user_has_farm_access(request.user, farm.id)

        # Convert keys to int for cohort IDs
        valuation_map = {}
        for k, v in valuation_map_raw.items():
            try:
                valuation_map[int(k)] = Decimal(str(v))
            except (ValueError, TypeError):
                error_response = Response(
                    {'error': f'قيمة غير صالحة في valuation_map: {k} → {v}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
                self._commit_action_idempotency(request, key, response=error_response)
                return error_response

        from smart_agri.finance.services.ias41_revaluation import IAS41RevaluationService
        results = IAS41RevaluationService.revalue_farm(farm, valuation_map, user=request.user)

        final_response = Response({
            'status': f'تمت إعادة تقييم {len(results)} دفعة(ات) بيولوجية بنجاح.',
            'results': results,
        })
        self._commit_action_idempotency(request, key, object_id=f"ias41:{farm.id}", response=final_response)
        return final_response

    @action(detail=False, methods=['post'], url_path='approve-manual-entries')
    def approve_manual_entries(self, request):
        """
        @idempotent
        [AGRI-GUARDIAN Phase 6] Maker-Checker Workflow
        Approves manual pending entries to make them immutable (is_posted=True).
        Accepts: {"farm_id": int, "entry_ids": [int]}
        """
        from rest_framework import status
        from rest_framework.response import Response

        if not user_has_sector_finance_authority(request.user) and not request.user.is_superuser:
            raise PermissionDenied("إعتماد القيود اليدوية يتطلب صلاحية مدير مالي قطاعي.")

        farm_id = request.data.get('farm_id')
        entry_ids = request.data.get('entry_ids', [])

        if not farm_id or not entry_ids:
            return Response({"error": "farm_id and entry_ids are required."}, status=status.HTTP_400_BAD_REQUEST)

        _ensure_user_has_farm_access(request.user, farm_id)

        key, error_response = self._enforce_action_idempotency(request, farm_id)
        if error_response: return error_response

        approved_count = LedgerApprovalService.approve_pending_entries(
            farm_id=int(farm_id),
            entry_ids=[int(entry_id) for entry_id in entry_ids],
            approver=request.user,
        )

        final_response = Response({
            "message": f"تم اعتماد {approved_count} قيود مالي بنجاح.",
            "approved_count": approved_count
        }, status=status.HTTP_200_OK)
        
        self._commit_action_idempotency(request, key, response=final_response)
        return final_response

    @action(detail=False, methods=['get'], url_path='material-variance-analysis')
    def material_variance_analysis(self, request):
        """
        [AGRI-GUARDIAN Phase 6] Deep Variance Analysis BI
        Computes accurate Qty Variance vs. Price Variance for direct materials.
        Accepts: ?crop_plan_id=1
        """
        if not user_has_sector_finance_authority(request.user) and not request.user.is_superuser:
            raise PermissionDenied("إجراء تحليل الانحراف المالي يتطلب صلاحية إدارة القطاع.")

        crop_plan, error_response = ensure_crop_plan_access(
            request=request, crop_plan_id=request.query_params.get('crop_plan_id')
        )
        if error_response:
            return error_response

        std_bom = build_standard_bom(crop_plan)
        std_bom = accumulate_actual_materials(crop_plan=crop_plan, std_bom=std_bom)
        variance_payload = compute_material_variance_report(std_bom)

        return Response({
            'crop_plan': crop_plan.name,
            **variance_payload,
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='allocate-overhead')
    def allocate_overhead(self, request):
        """
        @idempotent
        [AGRI-GUARDIAN Phase 6] Automated Overhead Allocation
        Distributes indirect expenses across active crop plans based on land area ratios.
        Accepts: {"farm_id": int, "period_start": "YYYY-MM-DD", "period_end": "YYYY-MM-DD"}
        """
        from smart_agri.finance.services.overhead_allocation import OverheadAllocationService

        if not user_has_sector_finance_authority(request.user) and not request.user.is_superuser:
            raise PermissionDenied("إجراء توزيع المصروفات العامة يتطلب صلاحية الإدارة العامة.")

        action_context = resolve_farm_action_context(request=request, viewset=self, farm_id=request.data.get('farm_id'))
        if isinstance(action_context, Response):
            return action_context
        farm = action_context.farm
        key = action_context.key

        period_start = request.data.get('period_start')
        period_end = request.data.get('period_end')
        ref_id = request.data.get('ref_id', '')

        if not period_start or not period_end:
            error_msg = Response({"error": "period_start and period_end are required."}, status=status.HTTP_400_BAD_REQUEST)
            self._commit_action_idempotency(request, key, response=error_msg)
            return error_msg

        try:
            results = OverheadAllocationService.allocate_indirect_expenses(
                farm=farm,
                period_start=period_start,
                period_end=period_end,
                user=request.user,
                ref_id=ref_id
            )
            final_response = Response({
                "message": f"Overhead expenses distributed successfully across active plans. {len(results)} ledger entries generated.",
                "allocated_entries": len(results)
            }, status=status.HTTP_200_OK)
            self._commit_action_idempotency(request, key, response=final_response)
            return final_response
        except (ValueError, TypeError, LookupError, DjangoValidationError) as e:
            logger.exception("API Error in allocate_overhead")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


    @action(detail=False, methods=['post'], url_path='liquidate-payroll')
    def liquidate_payroll(self, request):
        """
        @idempotent
        [AGRI-GUARDIAN Phase 6] Payroll Settlement (End-of-Month)
        Liquidates the Salaries Payable account against Cash/Bank.
        Accepts: {"farm_id": int, "payment_date": "YYYY-MM-DD", "credit_account": "1100-CASH", "ref_id": "string", "description": "string"}
        """
        from smart_agri.finance.services.core_finance import FinanceService

        if not user_has_sector_finance_authority(request.user) and not request.user.is_superuser:
            raise PermissionDenied("تسوية الرواتب تتطلب صلاحية مدير مالي.")

        action_context = resolve_farm_action_context(request=request, viewset=self, farm_id=request.data.get('farm_id'))
        if isinstance(action_context, Response):
            return action_context
        farm = action_context.farm
        key = action_context.key
            
        payment_date = request.data.get('payment_date')
        credit_account = request.data.get('credit_account')
        ref_id = request.data.get('ref_id', '')
        description = request.data.get('description', '')
        advances_amount = request.data.get('advances_recovery_amount', '0.0000')
        
        try:
            advances_recovery_amount = Decimal(str(advances_amount))
        except (InvalidOperation, ValueError, TypeError):
            logger.warning(
                "invalid_advances_recovery_amount event=PAYROLL_INVALID_ADVANCES_VALUE value=%s user_id=%s",
                advances_amount,
                getattr(request.user, "id", None),
            )
            return Response({"error": "Invalid value for advances_recovery_amount."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            entries = FinanceService.liquidate_payroll_account(
                farm=farm,
                user=request.user,
                payment_date=payment_date,
                credit_account=credit_account,
                ref_id=ref_id,
                description=description,
                advances_recovery_amount=advances_recovery_amount
            )
            if not entries:
                final_response = Response({"message": "No outstanding balance in Salaries Payable (2000-PAY-SAL)."}, status=status.HTTP_200_OK)
                self._commit_action_idempotency(request, key, response=final_response)
                return final_response
                
            entry_debit, entry_credit = entries
            debit_serializer = FinancialLedgerSerializer(entry_debit)
            credit_serializer = FinancialLedgerSerializer(entry_credit)
            
            final_response = Response({
                "message": "Payroll liquidated successfully.",
                "entries": [debit_serializer.data, credit_serializer.data]
            }, status=status.HTTP_201_CREATED)
            self._commit_action_idempotency(request, key, response=final_response)
            return final_response
        except (ValueError, TypeError, LookupError, DjangoValidationError) as e:
            logger.exception("API Error in liquidate_payroll")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='amortize-biological-assets')
    def amortize_biological_assets(self, request):
        """
        @idempotent
        [AGRI-GUARDIAN Phase 6] Biological Asset Amortization
        Transitions WIP to Biological Asset and amortizes PRODUCTIVE cohorts.
        """
        from smart_agri.finance.services.biological_amortization import BiologicalAmortizationService

        if not user_has_sector_finance_authority(request.user) and not request.user.is_superuser:
            raise PermissionDenied("اهلاك الأصول البيولوجية يتطلب صلاحية الإدارة العامة.")

        action_context = resolve_farm_action_context(request=request, viewset=self, farm_id=request.data.get('farm_id'))
        if isinstance(action_context, Response):
            return action_context
        farm = action_context.farm
        key = action_context.key

        period_date = request.data.get('period_date')
        ref_id = request.data.get('ref_id', '')

        try:
            results = BiologicalAmortizationService.amortize_productive_cohorts(
                farm=farm,
                user=request.user,
                period_date=period_date,
                ref_id=ref_id
            )
            final_response = Response({
                "message": f"Biological assets amortized successfully. Processed {len(results)} cohorts.",
                "results": results
            }, status=status.HTTP_200_OK)
            self._commit_action_idempotency(request, key, response=final_response)
            return final_response
        except (ValueError, TypeError, LookupError, DjangoValidationError) as e:
            logger.exception("API Error in amortize_biological_assets")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='close-seasonal-plan')
    def close_seasonal_plan(self, request):
        """
        @idempotent
        [AGRI-GUARDIAN Phase 6] Seasonal WIP Settlement
        Closes a seasonal Crop Plan and flushes residual WIP to COGS.
        """
        from smart_agri.finance.services.seasonal_settlement import SeasonalSettlementService
        from smart_agri.core.models.planning import CropPlan

        if not user_has_sector_finance_authority(request.user) and not request.user.is_superuser:
            raise PermissionDenied("إقفال الموسم يتطلب صلاحية الإدارة العامة.")

        farm_id = request.data.get('farm_id')
        crop_plan_id = request.data.get('crop_plan_id')

        if not farm_id or not crop_plan_id:
            return Response({"error": "farm_id and crop_plan_id are required."}, status=status.HTTP_400_BAD_REQUEST)

        action_context = resolve_farm_action_context(request=request, viewset=self, farm_id=farm_id)
        if isinstance(action_context, Response):
            return action_context
        farm = action_context.farm
        key = action_context.key

        try:
            crop_plan = CropPlan.objects.get(id=crop_plan_id)
        except CropPlan.DoesNotExist:
            return Response({"error": "Crop Plan not found."}, status=status.HTTP_404_NOT_FOUND)

        period_date = request.data.get('period_date')
        ref_id = request.data.get('ref_id', '')

        try:
            result = SeasonalSettlementService.close_seasonal_crop_plan(
                farm=farm,
                crop_plan=crop_plan,
                user=request.user,
                period_date=period_date,
                ref_id=ref_id
            )
            final_response = Response({
                "message": f"Seasonal Crop Plan {crop_plan.name} closed successfully.",
                "settlement_details": result
            }, status=status.HTTP_200_OK)
            self._commit_action_idempotency(request, key, response=final_response)
            return final_response
        except (ValueError, TypeError, LookupError, DjangoValidationError) as e:
            logger.exception("API Error in close_seasonal_plan")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
