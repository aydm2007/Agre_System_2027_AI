from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from decimal import Decimal
import logging
from django.db import DatabaseError, IntegrityError
from django.db.models import Sum
from smart_agri.core.models import (
    CropPlan,
    CropTemplate,
    CropTemplateTask,
    CropTemplateMaterial,
    Activity,
    CropPlanBudgetLine,
    PlanImportLog,
    PlannedMaterial,
    HarvestLot,
    SharecroppingContract,
)
from smart_agri.core.api.serializers import (
    CropPlanSerializer,
    CropTemplateSerializer,
    CropTemplateTaskSerializer,
    CropTemplateMaterialSerializer,
    PlannedActivitySerializer,
    PlannedMaterialSerializer,
    CropPlanBudgetLineSerializer,
    PlanImportLogSerializer,
    SharecroppingContractSerializer,
)
# Fix for missing HarvestLogSerializer (using alias)
try:
    from smart_agri.core.api.serializers.inventory import HarvestLogSerializer
except ImportError:
    # Fallback if alias import fails directly
    from smart_agri.core.api.serializers import HarvestLotSerializer as HarvestLogSerializer

from .base import AuditedModelViewSet

logger = logging.getLogger(__name__)

class CropPlanViewSet(AuditedModelViewSet):
    serializer_class = CropPlanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = CropPlan.objects.filter(deleted_at__isnull=True).order_by('-start_date')
        
        farm_id = self.request.query_params.get('farm_id') or self.request.query_params.get('farm')
        if farm_id:
            try:
                if ',' in str(farm_id):
                    fids = [int(x) for x in str(farm_id).split(',') if x.strip().isdigit()]
                    if fids: qs = qs.filter(farm_id__in=fids)
                else:
                    qs = qs.filter(farm_id=int(farm_id))
            except (ValueError, TypeError):
                pass
                
        location_id = self.request.query_params.get('location_id')
        if location_id:
            try:
                if ',' in str(location_id):
                    lids = [int(x) for x in str(location_id).split(',') if x.strip().isdigit()]
                    if lids:
                        qs = qs.filter(plan_locations__location_id__in=lids).distinct()
                else:
                    qs = qs.filter(plan_locations__location_id=int(location_id)).distinct()
            except (ValueError, TypeError):
                pass
                
        crop_id = self.request.query_params.get('crop') or self.request.query_params.get('crop_id')
        if crop_id:
            try:
                qs = qs.filter(crop_id=int(crop_id))
            except (ValueError, TypeError):
                pass

        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)

        return qs


    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        """
        [AGRI-GUARDIAN] Activate a CropPlan — transitions status to ACTIVE.
        Called by the frontend via CropPlans.approve(id).
        Validates that required fields are set before activation.
        """
        from smart_agri.core.models import AuditLog
        plan = self.get_object()
        key, error_response = self._enforce_action_idempotency(request, farm_id=getattr(plan, "farm_id", None))
        if error_response:
            return error_response

        # Guard: already active
        current_status = str(getattr(plan, 'status', '') or '').upper()
        if current_status == 'ACTIVE':
            response = Response(
                {'detail': 'الخطة فعّالة بالفعل.'},
                status=status.HTTP_200_OK
            )
            self._commit_action_idempotency(request, key, object_id=str(plan.pk), response=response)
            return response

        # Guard: missing required fields
        missing = []
        if not getattr(plan, 'crop_id', None) and not getattr(plan, 'crop', None):
            missing.append('المحصول')
        if not getattr(plan, 'start_date', None):
            missing.append('تاريخ البداية')
        if not getattr(plan, 'end_date', None):
            missing.append('تاريخ النهاية')
        if missing:
            return Response(
                {'detail': f'لا يمكن اعتماد الخطة. الحقول المطلوبة ناقصة: {", ".join(missing)}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Activate
        plan.status = 'ACTIVE'
        plan.save(update_fields=['status'])

        # Audit log (best-effort)
        try:
            AuditLog.objects.create(
                actor=request.user,
                action='CROP_PLAN_APPROVED',
                model='CropPlan',
                object_id=str(plan.pk),
                reason=f'الخطة "{plan.name}" تم اعتمادها وتفعيلها.',
                new_payload={'status': 'ACTIVE', 'plan_id': plan.pk, 'plan_name': plan.name},
            )
        except (DatabaseError, IntegrityError, ValueError, TypeError) as exc:
            logger.warning("CropPlan approval audit logging failed for plan=%s: %s", plan.pk, exc)

        serializer = self.get_serializer(plan)
        response = Response(serializer.data, status=status.HTTP_200_OK)
        self._commit_action_idempotency(request, key, object_id=str(plan.pk), response=response)
        return response

    @action(detail=True, methods=['get'])
    def variance(self, request, pk=None):
        """
        [Agri-Guardian] Calculate Budget vs Actual Variance.
        Returns:
        - planned_cost (Budget Total)
        - actual_cost (Realized Activity Costs)
        - variance (Actual - Budget)
        - variance_percentage
        """
        plan = self.get_object()
        actual = plan.actual_cost or Decimal('0')
        budget = plan.budget_total or Decimal('0')
        
        # Avoid DivisionByZero
        variance_val = actual - budget
        variance_pct = Decimal('0')
        if budget > 0:
            variance_pct = (variance_val / budget) * 100
            
        task_budgets = (
            CropPlanBudgetLine.objects.filter(crop_plan=plan, deleted_at__isnull=True)
            .values('task_id', 'task__name')
            .annotate(budget_total=Sum('total_budget'))
        )
        budget_by_task = {row['task_id']: {'budget': row['budget_total'] or Decimal('0'), 'name': row.get('task__name')} for row in task_budgets}

        task_actuals = (
            Activity.objects.filter(crop_plan=plan, deleted_at__isnull=True)
            .values('task_id', 'task__name')
            .annotate(actual_total=Sum('cost_total'))
        )
        actual_by_task = {row['task_id']: {'actual': row['actual_total'] or Decimal('0'), 'name': row.get('task__name')} for row in task_actuals}

        task_ids = sorted({*budget_by_task.keys(), *actual_by_task.keys()}, key=lambda value: value or 0)
        task_breakdown = [
            {
                "task_id": task_id,
                "task_name": budget_by_task.get(task_id, {}).get('name') or actual_by_task.get(task_id, {}).get('name') or "---",
                "budget_total": budget_by_task.get(task_id, {}).get('budget', Decimal('0')),
                "actual_total": actual_by_task.get(task_id, {}).get('actual', Decimal('0')),
            }
            for task_id in task_ids
        ]

        data = {
            # New frontend contract
            "budget": {"total": budget},
            "actual": {"total": actual},
            "tasks": task_breakdown,
            "currency": plan.currency or "YER",
            # Backward compatibility
            "planned_cost": budget,
            "actual_cost": actual,
            "variance": variance_val,
            "variance_percentage": round(variance_pct, 2),
            "revenue": plan.total_revenue,
            "roi": round(plan.roi, 2),
            "std_dev_total": Decimal('0.00'),
        }
        return Response(data)

    @action(detail=True, methods=['get'])
    def financial_summary(self, request, pk=None):
        """
        [Agri-Guardian] Real P&L Summary from the Ledger for this Crop Plan.
        """
        from smart_agri.finance.models import FinancialLedger
        from django.db.models import F
        plan = self.get_object()
        
        # We need to sum up costs by component. Expenses are Debit in WIP/Material/Labor/Machinery/Overhead.
        expenses = FinancialLedger.objects.filter(
            crop_plan=plan,
            account_code__in=[
                FinancialLedger.ACCOUNT_WIP,
                FinancialLedger.ACCOUNT_MATERIAL,
                FinancialLedger.ACCOUNT_LABOR,
                FinancialLedger.ACCOUNT_MACHINERY,
                FinancialLedger.ACCOUNT_OVERHEAD,
                FinancialLedger.ACCOUNT_COGS,
            ]
        ).values('analytical_tags__cost_component').annotate(
            net_expense=Sum(F('debit') - F('credit'))
        )
        
        # Revenue is Credit in Sales Revenue
        revenue_calc = FinancialLedger.objects.filter(
            crop_plan=plan,
            account_code=FinancialLedger.ACCOUNT_SALES_REVENUE
        ).aggregate(
            net_revenue=Sum(F('credit') - F('debit'))
        )
        net_revenue = revenue_calc['net_revenue'] or Decimal('0')
        
        breakdown = {
            "labor": Decimal('0'),
            "material": Decimal('0'),
            "machinery": Decimal('0'),
            "overhead": Decimal('0'),
            "other": Decimal('0'),
        }
        
        total_expense = Decimal('0')
        for exp in expenses:
            comp = exp.get('analytical_tags__cost_component')
            val = exp['net_expense'] or Decimal('0')
            if comp in breakdown:
                breakdown[comp] += val
            else:
                breakdown["other"] += val
            total_expense += val
            
        return Response({
            "currency": plan.currency or "YER",
            "total_expense": total_expense,
            "total_revenue": net_revenue,
            "net_profit": net_revenue - total_expense,
            "cost_breakdown": breakdown,
        })

    @action(detail=False, methods=['get'], url_path='financial-risk-zone')
    def financial_risk_zone(self, request):
        """
        Summarize material overrun risk by crop plan/material.
        Keeps the reports page on a stable, scoped endpoint and never 500s on
        valid farm/crop filters.
        """
        from smart_agri.core.models.activity import ActivityItem
        from smart_agri.core.models.crop import CropRecipeMaterial

        farm_id = request.query_params.get('farm_id') or request.query_params.get('farm')
        crop_id = request.query_params.get('crop_id') or request.query_params.get('crop')
        season_id = request.query_params.get('season_id') or request.query_params.get('season')

        if not farm_id or not crop_id:
            return Response({'results': []})

        try:
            crop_id = int(str(crop_id).strip())
        except (TypeError, ValueError):
            return Response({'results': []})

        plans = CropPlan.objects.filter(
            deleted_at__isnull=True,
            farm_id=farm_id,
            crop_id=crop_id,
        ).select_related('crop', 'season')
        if season_id:
            plans = plans.filter(season_id=season_id)

        results = []
        for plan in plans:
            if not plan.recipe_id:
                continue

            plan_area = plan.area or Decimal('1.0000')
            bom_materials = CropRecipeMaterial.objects.filter(
                recipe_id=plan.recipe_id,
                deleted_at__isnull=True,
            ).select_related('item')

            for bom in bom_materials:
                item = bom.item
                std_qty_per_ha = getattr(bom, 'standard_qty_per_ha', Decimal('0.0000')) or Decimal('0.0000')
                std_price = getattr(item, 'unit_price', Decimal('0.0000')) or Decimal('0.0000')
                standard_qty = std_qty_per_ha * plan_area
                standard_cost = standard_qty * std_price

                actuals = ActivityItem.objects.filter(
                    activity__crop_plan=plan,
                    item=item,
                    deleted_at__isnull=True,
                ).aggregate(
                    actual_qty=Sum('qty'),
                    actual_cost=Sum('total_cost'),
                )
                actual_cost = actuals.get('actual_cost') or Decimal('0.0000')
                deviation = actual_cost - standard_cost
                if deviation <= Decimal('0.0000'):
                    continue

                results.append({
                    'crop_plan_id': plan.id,
                    'crop_plan_name': plan.name,
                    'task_name': item.name or 'غير محدد',
                    'date': getattr(plan.start_date, 'isoformat', lambda: None)(),
                    'cost_total': str(actual_cost.quantize(Decimal('0.0001'))),
                    'mean': str(standard_cost.quantize(Decimal('0.0001'))),
                    'threshold': str(standard_cost.quantize(Decimal('0.0001'))),
                    'risk_score': str(deviation.quantize(Decimal('0.0001'))),
                    'deviation': str(deviation.quantize(Decimal('0.0001'))),
                })

        results.sort(key=lambda entry: Decimal(entry['deviation']), reverse=True)
        return Response({'results': results})

class CropTemplateViewSet(AuditedModelViewSet):
    queryset = CropTemplate.objects.filter(deleted_at__isnull=True)
    serializer_class = CropTemplateSerializer
    permission_classes = [IsAuthenticated]

# ... (Include other viewsets like PlannedActivityViewSet if needed)
class PlannedActivityViewSet(AuditedModelViewSet):
    queryset = Activity.objects.filter(deleted_at__isnull=True)
    serializer_class = PlannedActivitySerializer
    permission_classes = [IsAuthenticated]

class CropPlanBudgetLineViewSet(AuditedModelViewSet):
    queryset = CropPlanBudgetLine.objects.all()
    serializer_class = CropPlanBudgetLineSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['crop_plan']

class PlanImportLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PlanImportLog.objects.all().order_by('-created_at')
    serializer_class = PlanImportLogSerializer
    permission_classes = [IsAuthenticated]

class HarvestLogViewSet(AuditedModelViewSet):
    """
    [Agri-Guardian] Restored Endpoint for /harvest-logs/
    Maps to 'HarvestLot' model but exposed as 'harvest-logs' for frontend compatibility.
    """
    queryset = HarvestLot.objects.filter(deleted_at__isnull=True).order_by('-created_at')
    serializer_class = HarvestLogSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['crop_plan', 'batch_number'] 

class CropTemplateTaskViewSet(AuditedModelViewSet):
    queryset = CropTemplateTask.objects.all()
    serializer_class = CropTemplateTaskSerializer
    permission_classes = [IsAuthenticated]


class CropTemplateMaterialViewSet(AuditedModelViewSet):
    queryset = CropTemplateMaterial.objects.all()
    serializer_class = CropTemplateMaterialSerializer
    permission_classes = [IsAuthenticated]


class PlannedMaterialViewSet(AuditedModelViewSet):
    queryset = PlannedMaterial.objects.all()
    serializer_class = PlannedMaterialSerializer
    permission_classes = [IsAuthenticated]

class SharecroppingContractViewSet(AuditedModelViewSet):
    queryset = SharecroppingContract.objects.filter(deleted_at__isnull=True)
    serializer_class = SharecroppingContractSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['crop_plan']
