"""
Crop ViewSets
"""
from decimal import Decimal
from typing import Any
from django.db.models import Prefetch, Count, Q, Value, Max, Min, Sum
from django.db.models.functions import Coalesce
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError

from smart_agri.core.models import (
    Crop, FarmCrop, CropVariety, CropProduct, Task, 
    TreeProductivityStatus, TreeLossReason, TreeServiceCoverage, LocationTreeStock,
    CropMaterial, Farm, CropRecipe, CropRecipeMaterial, CropRecipeTask
)
from smart_agri.core.models.settings import FarmSettings
from smart_agri.core.services.mode_policy_service import policy_snapshot_for_farm
from smart_agri.core.api.serializers import (
    CropSerializer, FarmCropSerializer, CropVarietySerializer, 
    CropProductSerializer, TaskSerializer,
    TreeProductivityStatusSerializer, TreeLossReasonSerializer,
    CropMaterialSerializer, CropRecipeSerializer, CropRecipeMaterialSerializer, CropRecipeTaskSerializer
)
from smart_agri.core.api.permissions import (
    user_farm_ids, 
    _ensure_user_has_farm_access, 
    _limit_queryset_to_user_farms
)
# from smart_agri.core.api.utils import _coerce_bool
from .base import AuditedModelViewSet

class CropViewSet(AuditedModelViewSet):
    serializer_class = CropSerializer
    
    def get_queryset(self) -> Any:
        qs = Crop.objects.all().filter(deleted_at__isnull=True)
        farm_id = self.request.query_params.get('farm_id')
        crop_plan_id = self.request.query_params.get('crop_plan_id')
        
        if crop_plan_id:
            try:
                from smart_agri.core.models import CropPlan
                if ',' in str(crop_plan_id):
                    pids = [int(x) for x in str(crop_plan_id).split(',') if x.strip().isdigit()]
                    if pids: 
                        plan_crops = CropPlan.objects.filter(id__in=pids, deleted_at__isnull=True).values_list('crop_id', flat=True)
                        qs = qs.filter(id__in=plan_crops)
                else:
                    plan_crops = CropPlan.objects.filter(id=int(crop_plan_id), deleted_at__isnull=True).values_list('crop_id', flat=True)
                    qs = qs.filter(id__in=plan_crops)
            except (ValueError, TypeError):
                pass
        
        if farm_id:
            try:
                # [FIX]: Handle CSV farm_id safely
                if ',' in str(farm_id):
                    fids = [int(x) for x in str(farm_id).split(',') if x.strip().isdigit()]
                    # Check access for ALL provided farms (strict) or allow if access to ANY? 
                    # Standard pattern: specific farm access requires membership.
                    for fid in fids:
                        _ensure_user_has_farm_access(self.request.user, fid)
                    target_ids = fids
                else:
                    target_ids = [int(farm_id)]
                    _ensure_user_has_farm_access(self.request.user, target_ids[0])
                
                farm_crops = FarmCrop.objects.filter(
                    farm_id__in=target_ids,
                    deleted_at__isnull=True,
                ).values_list('crop_id', flat=True)
                return qs.filter(id__in=farm_crops).order_by('id')
            except (ValueError, TypeError, PermissionDenied):
                # Return empty or ignore constraint?
                # If specific farm requested but invalid/forbidden, we should return empty.
                return qs.none()

        if not self.request.user.is_superuser:
            user_farms = user_farm_ids(self.request.user)
            if not user_farms:
                return qs.none()
            
            farm_crops = FarmCrop.objects.filter(
                farm_id__in=user_farms,
                deleted_at__isnull=True,
            ).values_list('crop_id', flat=True)
            qs = qs.filter(id__in=farm_crops)

        return qs.order_by('id')


class FarmCropViewSet(AuditedModelViewSet):
    serializer_class = FarmCropSerializer
    
    def get_queryset(self) -> Any:
        ids = user_farm_ids(self.request.user)
        qs = FarmCrop.objects.all().filter(deleted_at__isnull=True)
        return qs.filter(farm_id__in=ids) if not self.request.user.is_superuser else qs


class CropVarietyViewSet(AuditedModelViewSet):
    serializer_class = CropVarietySerializer

    def _parse_location_ids(self):
        raw = self.request.query_params.get('location_ids')
        if not raw:
            return []
        return [int(loc.strip()) for loc in str(raw).split(',') if loc.strip().isdigit()]

    def _build_variety_location_map(self, crop_id, location_ids):
        if not location_ids:
            return {}

        qs = LocationTreeStock.objects.select_related('crop_variety').filter(
            deleted_at__isnull=True,
            location_id__in=location_ids,
            crop_variety__deleted_at__isnull=True,
        )
        if crop_id:
            qs = qs.filter(crop_variety__crop_id=crop_id)

        selected_locations = set(location_ids)
        grouped = {}
        for stock in qs:
            variety = stock.crop_variety
            if not variety:
                continue
            entry = grouped.setdefault(
                variety.id,
                {
                    'variety_name': variety.name,
                    'location_ids': [],
                    'available_in_all_locations': False,
                    'current_tree_count_total': 0,
                    'current_tree_count_by_location': {},
                },
            )
            if stock.location_id not in entry['location_ids']:
                entry['location_ids'].append(stock.location_id)
            quantity = int(getattr(stock, 'current_tree_count', 0) or 0)
            entry['current_tree_count_total'] += quantity
            entry['current_tree_count_by_location'][str(stock.location_id)] = quantity

        from smart_agri.core.models.inventory import BiologicalAssetCohort
        cohorts_qs = BiologicalAssetCohort.objects.select_related('variety').filter(
            deleted_at__isnull=True,
            location_id__in=location_ids,
            variety__deleted_at__isnull=True,
            status__in=[
                 BiologicalAssetCohort.STATUS_JUVENILE,
                 BiologicalAssetCohort.STATUS_PRODUCTIVE,
                 BiologicalAssetCohort.STATUS_RENEWING,
                 BiologicalAssetCohort.STATUS_SICK,
            ]
        )
        if crop_id:
            cohorts_qs = cohorts_qs.filter(crop_id=crop_id)
            
        for row in cohorts_qs:
            vid = row.variety_id
            if not vid: continue
            entry = grouped.setdefault(
                vid,
                {
                    'variety_name': row.variety.name if row.variety else '',
                    'location_ids': [],
                    'available_in_all_locations': False,
                    'current_tree_count_total': 0,
                    'current_tree_count_by_location': {},
                }
            )
            if row.location_id not in entry['location_ids']:
                entry['location_ids'].append(row.location_id)

        for entry in grouped.values():
            locations_present = set(entry['location_ids'])
            entry['location_ids'] = sorted(entry['location_ids'])
            entry['available_in_all_locations'] = bool(selected_locations) and locations_present == selected_locations
        return grouped

    def get_queryset(self):
        qs = CropVariety.objects.select_related('crop').filter(deleted_at__isnull=True)
        crop_id = self.request.query_params.get('crop') or self.request.query_params.get('crop_id')
        if crop_id:
            from django.db.models import Q
            qs = qs.filter(Q(crop_id=crop_id) | Q(crop__isnull=True))
        

        farm_id = self.request.query_params.get('farm') or self.request.query_params.get('farm_id')
        user = getattr(self.request, 'user', None)
        
        if farm_id and farm_id not in ['null', 'undefined', '']:
            try:
                farm_ids_list = [int(fid.strip()) for fid in str(farm_id).split(',') if fid.strip().isdigit()]
                if farm_ids_list:
                    from django.db.models import Q
                    qs = qs.filter(
                        Q(crop__farm_links__farm_id__in=farm_ids_list, crop__farm_links__deleted_at__isnull=True) |
                        Q(crop__isnull=True)
                    )
            except ValueError:
                pass
        elif user and user.is_authenticated and not user.is_superuser:
            farm_ids = user_farm_ids(user)
            if farm_ids:
                from django.db.models import Q
                qs = qs.filter(
                    Q(crop__farm_links__farm_id__in=farm_ids, crop__farm_links__deleted_at__isnull=True) |
                    Q(crop__isnull=True)
                )
            else:
                qs = qs.none()
        location_ids = self._parse_location_ids()
        if location_ids:
            variety_location_map = self._build_variety_location_map(crop_id, location_ids)
            if variety_location_map:
                qs = qs.filter(id__in=variety_location_map.keys())
            else:
                qs = qs.none()
        return qs.order_by('name', 'id').distinct()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        crop_id = self.request.query_params.get('crop') or self.request.query_params.get('crop_id')
        location_ids = self._parse_location_ids()
        if location_ids:
            context['variety_location_map'] = self._build_variety_location_map(crop_id, location_ids)
        return context


class CropProductViewSet(AuditedModelViewSet):
    serializer_class = CropProductSerializer
    queryset = (
        CropProduct.objects.filter(deleted_at__isnull=True)
        .select_related('crop', 'farm')
        .prefetch_related('unit_options__unit')
    )
    model_name = "CropProduct"

    def _accessible_farm_ids(self):
        if not hasattr(self, '_cached_farm_ids'):
            self._cached_farm_ids = list(user_farm_ids(self.request.user))
        return self._cached_farm_ids

    def _accessible_crop_ids(self):
        if not hasattr(self, '_cached_crop_ids'):
            if self.request.user.is_superuser:
                self._cached_crop_ids = list(
                    Crop.objects.filter(deleted_at__isnull=True).values_list('id', flat=True)
                )
            else:
                farm_ids = user_farm_ids(self.request.user)
                self._cached_crop_ids = list(
                    FarmCrop.objects.filter(
                        farm_id__in=farm_ids,
                        deleted_at__isnull=True,
                    ).values_list('crop_id', flat=True)
                )
        return self._cached_crop_ids

    def get_queryset(self) -> Any:
        qs = super().get_queryset()
        crop_id = self.request.query_params.get('crop') or self.request.query_params.get('crop_id')
        farm_id = self.request.query_params.get('farm') or self.request.query_params.get('farm_id')
        if crop_id:
            qs = qs.filter(crop_id=crop_id)
        if farm_id:
            try:
                valid_fids = []
                if ',' in str(farm_id):
                    candidate_fids = [int(x) for x in str(farm_id).split(',') if x.strip().isdigit()]
                    for fid in candidate_fids:
                        try:
                            _ensure_user_has_farm_access(self.request.user, fid)
                            valid_fids.append(fid)
                        except (PermissionDenied, ValueError, TypeError):
                            # [AGRI-GUARDIAN §2.II] Skip invalid farm IDs
                            continue
                else:
                     fid = int(farm_id)
                     _ensure_user_has_farm_access(self.request.user, fid)
                     valid_fids.append(fid)

                if valid_fids:
                     crop_ids = list(FarmCrop.objects.filter(
                         farm_id__in=valid_fids,
                         deleted_at__isnull=True,
                     ).values_list('crop_id', flat=True))
                     if crop_ids:
                         # Filter to farm-specific AND global products whose crops match the farm
                         qs = qs.filter(
                             Q(farm_id__in=valid_fids) |
                             Q(farm__isnull=True, crop_id__in=crop_ids)
                         )
                     else:
                         # No FarmCrop records → include farm-specific AND ALL global products
                         qs = qs.filter(
                             Q(farm_id__in=valid_fids) |
                             Q(farm__isnull=True)
                         )
                else:
                    return qs.none() 
            except (ValueError, TypeError):
                 return qs.none()
        if self.request.user.is_superuser:
            return qs
        accessible_farm_ids = self._accessible_farm_ids()
        accessible_crop_ids = self._accessible_crop_ids()
        if not accessible_farm_ids and not accessible_crop_ids:
            return qs.none()
        return qs.filter(
            Q(farm_id__in=accessible_farm_ids) |
            Q(farm__isnull=True, crop_id__in=accessible_crop_ids)
        )


class CropMaterialViewSet(AuditedModelViewSet):
    serializer_class = CropMaterialSerializer
    queryset = (
        CropMaterial.objects.filter(deleted_at__isnull=True)
        .select_related('crop', 'item', 'item__unit', 'recommended_unit')
    )
    model_name = "CropMaterial"

    def _accessible_crop_ids(self):
        if not hasattr(self, '_cached_material_crop_ids'):
            if self.request.user.is_superuser:
                self._cached_material_crop_ids = list(
                    Crop.objects.filter(deleted_at__isnull=True).values_list('id', flat=True)
                )
            else:
                farm_ids = user_farm_ids(self.request.user)
                self._cached_material_crop_ids = list(
                    FarmCrop.objects.filter(
                        farm_id__in=farm_ids,
                        deleted_at__isnull=True,
                    ).values_list('crop_id', flat=True)
                )
        return self._cached_material_crop_ids

    def get_queryset(self) -> Any:
        qs = super().get_queryset()
        crop_id = self.request.query_params.get('crop') or self.request.query_params.get('crop_id')
        farm_id = self.request.query_params.get('farm_id') or self.request.query_params.get('farm')
        if crop_id:
            qs = qs.filter(crop_id=crop_id)
        if farm_id:
            try:
                valid_fids = []
                if ',' in str(farm_id):
                     candidate_fids = [int(x) for x in str(farm_id).split(',') if x.strip().isdigit()]
                     for fid in candidate_fids:
                         try:
                             _ensure_user_has_farm_access(self.request.user, fid)
                             valid_fids.append(fid)
                         except (PermissionDenied, ValueError, TypeError):
                             # [AGRI-GUARDIAN §2.II] Skip invalid farm IDs
                             continue
                else:
                     fid = int(farm_id)
                     _ensure_user_has_farm_access(self.request.user, fid)
                     valid_fids = [fid]
                
                if valid_fids:
                    crop_ids = FarmCrop.objects.filter(
                        farm_id__in=valid_fids,
                        deleted_at__isnull=True,
                    ).values_list('crop_id', flat=True)
                    qs = qs.filter(crop_id__in=crop_ids)
                else:
                    return qs.none()
            except (ValueError, TypeError):
                return qs.none()
        if self.request.user.is_superuser:
            return qs
        accessible_crop_ids = self._accessible_crop_ids()
        if not accessible_crop_ids:
            return qs.none()
        return qs.filter(crop_id__in=accessible_crop_ids)


class TaskViewSet(AuditedModelViewSet):
    serializer_class = TaskSerializer
    
    def get_queryset(self) -> Any:
        # Use super() to inherit base filtering (e.g. soft delete from AuditedModelViewSet)
        # If AuditedModelViewSet doesn't return Task queryset, we explicitly use Task.objects
        # But usually AuditedModelViewSet is generic. Let's be safe and use Task.objects as before but robustly.
        queryset = Task.objects.filter(deleted_at__isnull=True)
        
        # 1. Safe Parameter Extraction
        crop_id = self.request.query_params.get('crop')
        farm_id = self.request.query_params.get('farm_id')

        # 2. Filter by Crop (with validation)
        if crop_id and crop_id not in ['null', 'undefined', '']:
            try:
                queryset = queryset.filter(crop_id=int(crop_id))
            except (ValueError, TypeError):
                pass # Ignore invalid crop_id
        
        # 3. Filter by Farm (Safe handling)
        # Tasks are linked to Crop, which is linked to Farm.
        # Handle comma-separated list of farm IDs (e.g. "1,2,3")
        if farm_id and farm_id not in ['null', 'undefined', '']:
            try:
                # [FIX]: Handle CSV string "10,1,12,11"
                farm_ids_list = [int(fid.strip()) for fid in str(farm_id).split(',') if fid.strip().isdigit()]
                if farm_ids_list:
                    queryset = queryset.filter(
                        crop__farm_links__farm_id__in=farm_ids_list,
                        crop__farm_links__deleted_at__isnull=True,
                    )
            except (ValueError, TypeError):
                pass


        return queryset.distinct().order_by('id')


class TreeProductivityStatusViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TreeProductivityStatusSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = TreeProductivityStatus.objects.all().order_by('code')


class TreeLossReasonViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TreeLossReasonSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = TreeLossReason.objects.all().order_by('code')


# ---- Cards ViewSets (Dashboard) ----

class CropCardViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        farm_id = request.query_params.get('farm_id')
        target_farm_ids = None
        if farm_id:
            try:
                if ',' in str(farm_id):
                     fids = [int(x) for x in str(farm_id).split(',') if x.strip().isdigit()]
                     for fid in fids:
                         _ensure_user_has_farm_access(request.user, fid)
                     target_farm_ids = fids
                else:
                    farm_id_int = int(farm_id)
                    _ensure_user_has_farm_access(request.user, farm_id_int)
                    target_farm_ids = [farm_id_int]
            except (ValueError, TypeError, PermissionDenied):
                 return Response([], status=status.HTTP_200_OK)
        elif not request.user.is_superuser:
            target_farm_ids = user_farm_ids(request.user)
            if not target_farm_ids:
                return Response([], status=status.HTTP_200_OK)

        crop_filter_ids = None
        if target_farm_ids is not None:
            crop_filter_ids = list(
                FarmCrop.objects.filter(
                    farm_id__in=target_farm_ids,
                    deleted_at__isnull=True,
                ).values_list('crop_id', flat=True)
            )
            if not crop_filter_ids:
                return Response([], status=status.HTTP_200_OK)

        tasks_qs = Task.objects.filter(deleted_at__isnull=True).order_by('stage', 'name')
        products_qs = CropProduct.objects.filter(deleted_at__isnull=True).select_related('item')

        crops_qs = Crop.objects.filter(deleted_at__isnull=True)
        if crop_filter_ids is not None:
            crops_qs = crops_qs.filter(id__in=crop_filter_ids)

        crops_qs = crops_qs.prefetch_related(
            Prefetch('tasks', queryset=tasks_qs, to_attr='prefetched_tasks'),
            Prefetch('products', queryset=products_qs, to_attr='prefetched_products'),
        ).order_by('name')

        crops = list(crops_qs)
        if not crops:
            return Response([], status=status.HTTP_200_OK)

        crop_ids = [crop.id for crop in crops]
        farm_links = (
            FarmCrop.objects.filter(crop_id__in=crop_ids, deleted_at__isnull=True)
            .select_related('farm')
        )
        farms_map: dict[int, list[dict[str, Any]]] = {}
        for link in farm_links:
            farms_map.setdefault(link.crop_id, []).append({'id': link.farm_id, 'name': link.farm.name})

        coverage_map: dict[int, list[dict[str, Any]]] = {}
        if crop_ids:
            coverage_qs = (
                TreeServiceCoverage.objects.filter(
                    activity__crop_id__in=crop_ids,
                    deleted_at__isnull=True,
                )
                .order_by('-created_at')
            )
            for coverage in coverage_qs:
                try:
                    activity = coverage.activity
                except ObjectDoesNotExist:
                    continue

                if not activity:
                    continue
                
                try:
                    # Accessing crop_id (integer) shouldn't raise DoesNotExist usually unless accessing related crop object
                    # But getattr(activity, 'crop_id') is safe if field is integer.
                    # However, if 'crop' property is accessed, it might.
                    # Use simple attribute access which is standard
                    crop_identifier = activity.crop_id
                except ObjectDoesNotExist:
                    continue

                if not crop_identifier:
                    continue

                try:
                    task = activity.task
                except ObjectDoesNotExist:
                    task = None

                timeline = coverage_map.setdefault(crop_identifier, [])
                if len(timeline) >= 6:
                    continue
                
                try:
                    log = activity.log
                    log_date = log.log_date if log else None
                except ObjectDoesNotExist:
                    log = None
                    log_date = None
                
                timeline.append(
                    {
                        'date': log_date or getattr(coverage, 'created_at', None),
                        'service_scope': coverage.service_scope,
                        'service_type': coverage.service_type,
                        'service_count': coverage.service_count,
                        'task_name': getattr(task, 'name', ''),
                        'task_stage': getattr(task, 'stage', ''),
                    }
                )

        cards = []
        for crop in crops:
            tasks_data = [
                {
                    'id': task.id,
                    'name': task.name,
                    'stage': task.stage,
                    'requires_machinery': task.requires_machinery,
                    'requires_well': task.requires_well,
                    'requires_area': task.requires_area,
                    'requires_tree_count': task.requires_tree_count,
                    'is_asset_task': task.is_asset_task,
                    'asset_type': task.asset_type,
                }
                for task in getattr(crop, 'prefetched_tasks', [])
            ]
            products_data = []
            for link in getattr(crop, 'prefetched_products', []):
                item = getattr(link, 'item', None)
                products_data.append(
                    {
                        'id': link.id,
                        'item_id': getattr(link, 'item_id', None),
                        'name': getattr(item, 'name', link.name) if item else link.name,
                        'group': getattr(item, 'group', '') if item else '',
                        'uom': getattr(item, 'uom', '') if item else '',
                        'category': getattr(item, 'group', ''),
                        'is_primary': link.is_primary,
                        'notes': link.notes,
                    }
                )

            services_total = len(tasks_data)
            machinery_tasks = sum(1 for task in tasks_data if task.get('requires_machinery') or task.get('is_asset_task'))
            asset_types = sorted({
                task['asset_type']
                for task in tasks_data
                if task.get('asset_type')
            })
            products_total = len(products_data)

            cards.append(
                {
                    'id': crop.id,
                    'name': crop.name,
                    'mode': crop.mode,
                    'is_perennial': crop.is_perennial,
                    'farms': farms_map.get(crop.id, []),
                    'services': tasks_data,
                    'products': products_data,
                    'primary_product_id': next((entry['id'] for entry in products_data if entry['is_primary']), None),
                    'metrics': {
                        'services_total': services_total,
                        'machinery_tasks': machinery_tasks,
                        'products_total': products_total,
                        'asset_types': asset_types,
                    },
                    'service_timeline': coverage_map.get(crop.id, []),
                }
            )

        return Response(cards, status=status.HTTP_200_OK)


class ServiceCardViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    CARD_TITLES = {
        'execution': 'التنفيذ',
        'materials': 'المواد',
        'labor': 'العمالة',
        'well': 'الري والبئر',
        'machinery': 'الآليات',
        'fuel': 'الوقود',
        'perennial': 'الخدمة المعمرة',
        'harvest': 'الحصاد',
        'control': 'الرقابة',
        'variance': 'الانحراف',
        'financial_trace': 'الأثر المالي',
    }
    SIMPLE_VISIBLE_FINANCE = {'operations_only', 'summarized_amounts', 'ratios_only'}

    @staticmethod
    def _parse_csv_ids(raw_value):
        if raw_value in [None, "", "null", "undefined"]:
            return []
        return [int(x) for x in str(raw_value).split(',') if str(x).strip().isdigit()]

    @staticmethod
    def _format_decimal(value, zero_decimal):
        decimal_value = value if isinstance(value, Decimal) else Decimal(str(value or zero_decimal))
        return str(decimal_value.quantize(zero_decimal))

    def _resolve_crop_plan(self, *, crop_id, target_farms, explicit_plan_id=None, target_date=None, location_ids=None):
        from smart_agri.core.models.planning import CropPlan

        plans = CropPlan.objects.filter(
            deleted_at__isnull=True,
            farm_id__in=target_farms,
            crop_id=crop_id,
        )
        if explicit_plan_id:
            plans = plans.filter(id=explicit_plan_id)
        else:
            active_status = getattr(CropPlan, 'status', None)
            if active_status is not None:
                plans = plans.filter(status__iexact='active')
            if target_date:
                plans = plans.filter(start_date__lte=target_date, end_date__gte=target_date)
        if location_ids:
            plans = plans.filter(plan_locations__location_id__in=location_ids).distinct()
        return plans.order_by('-start_date', '-id').first()

    @staticmethod
    def _resolve_policy_snapshot(target_farms):
        policy_snapshot, _settings_obj, _source, _resolved_farm_id = policy_snapshot_for_farm(
            farm_id=target_farms[0] if target_farms else None
        )
        return policy_snapshot

    def _build_execution_plan_metrics(
        self,
        *,
        plan,
        task,
        activity_qs,
        target_date,
        location_ids,
        zero_decimal,
    ):
        from smart_agri.core.models.planning import PlannedActivity

        if not plan:
            return {
                'plan_id': None,
                'plan_name': None,
                'plan_status': None,
                'planned_count': 0,
                'executed_count': activity_qs.count(),
                'planned_tasks': 0,
                'completed_tasks': 0,
                'plan_progress_pct': 0,
                'budget_total': self._format_decimal(zero_decimal, zero_decimal),
                'actual_total': self._format_decimal(zero_decimal, zero_decimal),
                'variance_total': self._format_decimal(zero_decimal, zero_decimal),
                'variance_pct': 0,
                'planned_locations': 0,
                'matched_locations': 0,
                'location_coverage_pct': 0.0,
                'schedule_status': 'no_plan',
            }

        planned_activities_qs = PlannedActivity.objects.filter(
            crop_plan=plan,
            deleted_at__isnull=True,
        )
        task_plans_qs = planned_activities_qs.filter(task=task) if task else planned_activities_qs.none()
        completed_activities_qs = plan.activities.filter(deleted_at__isnull=True)

        planned_tasks = planned_activities_qs.values('task_id').distinct().count()
        completed_tasks = completed_activities_qs.exclude(task_id__isnull=True).values('task_id').distinct().count()
        progress_pct = round((completed_tasks / planned_tasks) * 100, 2) if planned_tasks else 0

        budget_total = plan.budget_total or zero_decimal
        actual_total = completed_activities_qs.aggregate(
            total=Coalesce(Sum('cost_total'), Value(zero_decimal)),
        )['total'] or zero_decimal
        variance_total = actual_total - budget_total
        variance_pct = round((variance_total / budget_total) * 100, 2) if budget_total else 0

        plan_location_ids = list(
            plan.plan_locations.filter(deleted_at__isnull=True).values_list('location_id', flat=True)
        )
        matched_locations = len(set(plan_location_ids).intersection(set(location_ids or [])))
        location_coverage_pct = round((matched_locations / len(plan_location_ids)) * 100, 2) if plan_location_ids else 0.0

        planned_count = task_plans_qs.count()
        executed_count = activity_qs.count()
        schedule_status = 'unplanned'
        if planned_count:
            planned_today = bool(target_date and task_plans_qs.filter(planned_date=target_date).exists())
            if planned_today:
                schedule_status = 'due_today'
            else:
                bounds = task_plans_qs.aggregate(
                    earliest=Min('planned_date'),
                    latest=Max('planned_date'),
                )
                earliest_planned_date = bounds['earliest']
                latest_planned_date = bounds['latest']
                if target_date and latest_planned_date and latest_planned_date < target_date and executed_count < planned_count:
                    schedule_status = 'late'
                elif target_date and earliest_planned_date and earliest_planned_date > target_date:
                    schedule_status = 'ahead_of_plan'
                else:
                    schedule_status = 'planned'

        return {
            'plan_id': plan.id,
            'plan_name': plan.name,
            'plan_status': plan.status,
            'planned_count': planned_count,
            'executed_count': executed_count,
            'planned_tasks': planned_tasks,
            'completed_tasks': completed_tasks,
            'plan_progress_pct': progress_pct,
            'budget_total': self._format_decimal(budget_total, zero_decimal),
            'actual_total': self._format_decimal(actual_total, zero_decimal),
            'variance_total': self._format_decimal(variance_total, zero_decimal),
            'variance_pct': variance_pct,
            'planned_locations': len(plan_location_ids),
            'matched_locations': matched_locations,
            'location_coverage_pct': location_coverage_pct,
            'schedule_status': schedule_status,
        }

    @staticmethod
    def _safe_related(instance, relation_name):
        if not instance:
            return None
        try:
            return getattr(instance, relation_name, None)
        except ObjectDoesNotExist:
            return None

    @staticmethod
    def _card_status(*, has_data=False, risk=False, critical=False):
        if critical:
            return 'critical'
        if risk:
            return 'attention'
        if has_data:
            return 'ready'
        return 'idle'

    def _resolve_task_contract(self, *, task, activity):
        snapshot = getattr(activity, 'task_contract_snapshot', None) if activity else None
        if isinstance(snapshot, dict) and snapshot.get('smart_cards'):
            return snapshot
        if task:
            return task.get_effective_contract()
        return {}

    @staticmethod
    def _format_metric_value(value, zero_decimal):
        if isinstance(value, Decimal):
            return str(value.quantize(zero_decimal))
        return value

    def _resolve_visible_card_keys(self, *, contract, policy_snapshot):
        presentation = contract.get('presentation') if isinstance(contract, dict) else {}
        presentation = presentation if isinstance(presentation, dict) else {}
        mode = policy_snapshot.get('mode')
        preview_key = 'strict_preview' if mode == FarmSettings.MODE_STRICT else 'simple_preview'
        visible = presentation.get(preview_key) or presentation.get('card_order') or []
        return [card_key for card_key in visible if isinstance(card_key, str)]

    def _build_materials_metrics(self, *, plan, activity_qs, zero_decimal):
        planned_qty = zero_decimal
        planned_cost = zero_decimal
        actual_qty = zero_decimal
        actual_cost = zero_decimal
        line_items = []
        line_items_map = {}

        recipe = getattr(plan, 'recipe', None) if plan else None
        area = Decimal(str(getattr(plan, 'area', None) or 1))
        if recipe:
            for recipe_material in recipe.materials.select_related('item').all():
                item = getattr(recipe_material, 'item', None)
                item_id = getattr(item, 'id', None)
                if not item_id:
                    continue
                std_qty = (recipe_material.standard_qty_per_ha or zero_decimal) * area
                unit_cost = getattr(item, 'unit_price', zero_decimal) or zero_decimal
                std_cost = std_qty * unit_cost
                planned_qty += std_qty
                planned_cost += std_cost
                line_items_map[item_id] = {
                    'item_id': item_id,
                    'item_name': item.name,
                    'on_hand_qty': self._format_decimal(getattr(item, 'inventory_total', zero_decimal), zero_decimal),
                    'planned_qty': std_qty,
                    'actual_qty': zero_decimal,
                    'qty_variance': zero_decimal,
                    'planned_cost': std_cost,
                    'actual_cost': zero_decimal,
                    'cost_variance': zero_decimal,
                }

        for activity in activity_qs:
            for activity_item in activity.items.select_related('item').all():
                item = getattr(activity_item, 'item', None)
                item_id = getattr(item, 'id', None)
                if not item_id:
                    continue
                qty = activity_item.qty or zero_decimal
                cost_per_unit = activity_item.cost_per_unit or getattr(item, 'unit_price', zero_decimal) or zero_decimal
                total_cost = activity_item.total_cost or (qty * cost_per_unit)
                actual_qty += qty
                actual_cost += total_cost

                if item_id not in line_items_map:
                    line_items_map[item_id] = {
                        'item_id': item_id,
                        'item_name': item.name,
                        'on_hand_qty': self._format_decimal(getattr(item, 'inventory_total', zero_decimal), zero_decimal),
                        'planned_qty': zero_decimal,
                        'actual_qty': zero_decimal,
                        'qty_variance': zero_decimal,
                        'planned_cost': zero_decimal,
                        'actual_cost': zero_decimal,
                        'cost_variance': zero_decimal,
                    }
                item_entry = line_items_map[item_id]
                item_entry['actual_qty'] += qty
                item_entry['actual_cost'] += total_cost

        for item_entry in line_items_map.values():
            item_entry['qty_variance'] = item_entry['actual_qty'] - item_entry['planned_qty']
            item_entry['cost_variance'] = item_entry['actual_cost'] - item_entry['planned_cost']
            line_items.append(
                {
                    key: self._format_metric_value(value, zero_decimal)
                    for key, value in item_entry.items()
                }
            )

        qty_variance = actual_qty - planned_qty
        cost_variance = actual_cost - planned_cost
        return {
            'planned_qty': self._format_decimal(planned_qty, zero_decimal),
            'actual_qty': self._format_decimal(actual_qty, zero_decimal),
            'qty_variance': self._format_decimal(qty_variance, zero_decimal),
            'planned_cost': self._format_decimal(planned_cost, zero_decimal),
            'actual_cost': self._format_decimal(actual_cost, zero_decimal),
            'cost_variance': self._format_decimal(cost_variance, zero_decimal),
            'line_items': sorted(line_items, key=lambda item: item['item_name']),
        }

    def _build_card_entry(
        self,
        *,
        card_key,
        order,
        mode_visibility,
        metrics,
        flags,
        data_source,
        status,
        policy=None,
        source_refs=None,
    ):
        return {
            'card_key': card_key,
            'title': self.CARD_TITLES.get(card_key, card_key),
            'enabled': True,
            'order': order,
            'mode_visibility': mode_visibility,
            'status': status,
            'metrics': metrics,
            'flags': flags,
            'data_source': data_source,
            'policy': policy or {},
            'source_refs': source_refs or [],
        }

    def _build_smart_card_stack(
        self,
        *,
        task,
        activity_qs,
        sample_activity,
        policy_snapshot,
        selected_plan,
        target_date,
        location_ids,
        control_metrics,
        variance_metrics,
        ledger_metrics,
        health_flags,
        zero_decimal,
    ):
        stack = []
        mode_visibility = 'strict_preview' if policy_snapshot.get('mode') == FarmSettings.MODE_STRICT else 'simple_preview'
        cost_display_mode = policy_snapshot.get('cost_visibility')
        visibility_level = policy_snapshot.get('visibility_level')
        show_full_amounts = cost_display_mode == FarmSettings.COST_VISIBILITY_FULL
        show_summary_amounts = cost_display_mode in {
            FarmSettings.COST_VISIBILITY_SUMMARIZED,
            FarmSettings.COST_VISIBILITY_FULL,
        }

        if not task:
            stack.append(
                self._build_card_entry(
                    card_key='control',
                    order=0,
                    mode_visibility=mode_visibility,
                    metrics=control_metrics,
                    flags=['critical_control'] if control_metrics.get('critical_logs', 0) > 0 else [],
                    data_source='daily_log',
                    status=self._card_status(
                        has_data=control_metrics.get('total_logs', 0) > 0,
                        critical=control_metrics.get('critical_logs', 0) > 0,
                    ),
                    policy={'read_only': True},
                    source_refs=['daily_log'],
                )
            )
            stack.append(
                self._build_card_entry(
                    card_key='variance',
                    order=1,
                    mode_visibility=mode_visibility,
                    metrics=variance_metrics,
                    flags=['open_variance'] if variance_metrics.get('open_alerts', 0) > 0 else [],
                    data_source='variance_alert',
                    status=self._card_status(
                        has_data=variance_metrics.get('total_alerts', 0) > 0,
                        risk=variance_metrics.get('open_alerts', 0) > 0,
                    ),
                    policy={'read_only': True, 'per_card_classification': True},
                    source_refs=['variance_alert'],
                )
            )
            ledger_metrics_dict = {
                'entries_count': ledger_metrics.get('entries_count', 0),
                'cost_display_mode': cost_display_mode,
            }
            if show_summary_amounts:
                ledger_metrics_dict['debit_total'] = ledger_metrics.get('debit_total')
                ledger_metrics_dict['credit_total'] = ledger_metrics.get('credit_total')
                
            stack.append(
                self._build_card_entry(
                    card_key='financial_trace',
                    order=2,
                    mode_visibility=mode_visibility,
                    metrics=ledger_metrics_dict,
                    flags=[],
                    data_source='financial_ledger',
                    status=self._card_status(has_data=ledger_metrics.get('entries_count', 0) > 0),
                    policy={
                        'read_only': True,
                        'strict_detail_only': True,
                        'cost_display_mode': cost_display_mode,
                        'visibility_level': visibility_level,
                    },
                    source_refs=['financial_ledger'],
                )
            )
            return stack

        contract = self._resolve_task_contract(task=task, activity=sample_activity)
        visible_card_keys = self._resolve_visible_card_keys(contract=contract, policy_snapshot=policy_snapshot)
        smart_cards = contract.get('smart_cards') if isinstance(contract, dict) else {}
        smart_cards = smart_cards if isinstance(smart_cards, dict) else {}
        presentation = contract.get('presentation') if isinstance(contract, dict) else {}
        presentation = presentation if isinstance(presentation, dict) else {}
        card_order = presentation.get('card_order') or list(smart_cards.keys())
        order_index = {card_key: index for index, card_key in enumerate(card_order)}
        materials_metrics = self._build_materials_metrics(
            plan=selected_plan,
            activity_qs=activity_qs,
            zero_decimal=zero_decimal,
        )
        sample_irrigation = self._safe_related(sample_activity, 'irrigation_details')
        sample_machine = self._safe_related(sample_activity, 'machine_details')
        sample_harvest = self._safe_related(sample_activity, 'harvest_details')
        execution_plan_metrics = self._build_execution_plan_metrics(
            plan=selected_plan,
            task=task,
            activity_qs=activity_qs,
            target_date=target_date,
            location_ids=location_ids,
            zero_decimal=zero_decimal,
        )
        execution_metrics = {
            'task_id': task.id,
            'task_name': task.name,
            'stage': task.stage,
            **execution_plan_metrics,
            'daily_total_activities': activity_qs.count(),
            'daily_total_cost': self._format_decimal(
                activity_qs.aggregate(total=Coalesce(Sum('cost_total'), Value(zero_decimal)))['total']
                or zero_decimal,
                zero_decimal,
            ),
            'latest_log_date': sample_activity.log.log_date if sample_activity and sample_activity.log_id else None,
            'visibility_level': visibility_level,
            'cost_display_mode': cost_display_mode,
            'open_variances': variance_metrics.get('open_alerts', 0),
        }
        execution_flags = [
            flag
            for flag in health_flags
            if flag.startswith('task_') or flag in {'missing_active_plan', 'budget_overrun'}
        ]

        stack = []
        for card_key in visible_card_keys:
            card_config = smart_cards.get(card_key) or {}
            if not card_config.get('enabled', False):
                continue

            if card_key == 'execution':
                stack.append(
                    self._build_card_entry(
                        card_key=card_key,
                        order=order_index.get(card_key, 0),
                        mode_visibility=mode_visibility,
                        metrics=execution_metrics,
                        flags=execution_flags,
                        data_source='task_contract_snapshot',
                        status=self._card_status(
                            has_data=False, # Legacy fallback, will check daily log logic if needed
                            risk=(
                                'missing_active_plan' in execution_flags
                            ),
                        ),
                        policy={
                            'read_only': True,
                            'cost_display_mode': cost_display_mode,
                            'visibility_level': visibility_level,
                            'shadow_accounting': True,
                        },
                        source_refs=[
                            'activity',
                            'daily_log',
                            'daily_log.activities',
                            'crop_plan',
                            'planned_activity',
                            'crop_plan_budget',
                            'task_contract_snapshot',
                        ],
                    )
                )
            elif card_key == 'materials':
                metrics = {
                    'planned_qty': materials_metrics['planned_qty'],
                    'actual_qty': materials_metrics['actual_qty'],
                    'qty_variance': materials_metrics['qty_variance'],
                }
                if show_summary_amounts:
                    metrics.update(
                        {
                            'planned_cost': materials_metrics['planned_cost'],
                            'actual_cost': materials_metrics['actual_cost'],
                            'cost_variance': materials_metrics['cost_variance'],
                        }
                    )
                else:
                    planned_cost = Decimal(materials_metrics['planned_cost'])
                    actual_cost = Decimal(materials_metrics['actual_cost'])
                    ratio = round((actual_cost / planned_cost) * 100, 2) if planned_cost else 0
                    metrics['cost_ratio_pct'] = ratio
                if show_full_amounts:
                    metrics['line_items'] = materials_metrics['line_items']

                stack.append(
                    self._build_card_entry(
                        card_key=card_key,
                        order=order_index.get(card_key, 0),
                        mode_visibility=mode_visibility,
                        metrics=metrics,
                        flags=['budget_overrun'] if Decimal(materials_metrics['cost_variance']) > zero_decimal else [],
                        data_source='activity_items',
                        status=self._card_status(
                            has_data=Decimal(materials_metrics['actual_qty']) > zero_decimal
                            or Decimal(materials_metrics['planned_qty']) > zero_decimal,
                            risk=Decimal(materials_metrics['cost_variance']) > zero_decimal,
                        ),
                        policy={
                            'cost_visibility': cost_display_mode,
                            'visibility_level': visibility_level,
                            'full_cost_allowed': show_full_amounts,
                        },
                        source_refs=[
                            'activity.items',
                            'crop_plan.recipe',
                            'activity.cost_snapshots',
                            'financial_ledger',
                        ],
                    )
                )
            elif card_key == 'labor':
                total_workers = zero_decimal
                total_surrah = zero_decimal
                for activity in activity_qs:
                    for labor_row in activity.employee_details.all():
                        total_workers += labor_row.workers_count or zero_decimal
                        total_surrah += labor_row.surrah_share or zero_decimal
                stack.append(
                    self._build_card_entry(
                        card_key=card_key,
                        order=order_index.get(card_key, 0),
                        mode_visibility=mode_visibility,
                        metrics={
                            'workers_count': self._format_decimal(total_workers, zero_decimal),
                            'surrah_share': self._format_decimal(total_surrah, zero_decimal),
                        },
                        flags=[],
                        data_source='activity_employee',
                        status=self._card_status(has_data=total_workers > zero_decimal or total_surrah > zero_decimal),
                        policy={'surra_law': True, 'backend_costing_only': True},
                        source_refs=['activity.employee_details'],
                    )
                )
            elif card_key == 'well':
                water_volume = getattr(sample_irrigation, 'water_volume', zero_decimal) or zero_decimal
                stack.append(
                    self._build_card_entry(
                        card_key=card_key,
                        order=order_index.get(card_key, 0),
                        mode_visibility=mode_visibility,
                        metrics={
                            'water_volume': self._format_decimal(water_volume, zero_decimal),
                            'uom': getattr(sample_irrigation, 'uom', 'm3') if sample_irrigation else 'm3',
                            'well_reading': self._format_metric_value(
                                getattr(sample_irrigation, 'well_reading', None),
                                zero_decimal,
                            ),
                        },
                        flags=[],
                        data_source='activity_irrigation',
                        status=self._card_status(has_data=bool(sample_irrigation and water_volume > zero_decimal)),
                        policy={'variance_surface': True},
                        source_refs=['activity.irrigation_details'],
                    )
                )
            elif card_key == 'machinery':
                machine_hours = getattr(sample_machine, 'machine_hours', zero_decimal) or zero_decimal
                stack.append(
                    self._build_card_entry(
                        card_key=card_key,
                        order=order_index.get(card_key, 0),
                        mode_visibility=mode_visibility,
                        metrics={
                            'machine_hours': self._format_decimal(machine_hours, zero_decimal),
                            'asset_type': getattr(task, 'asset_type', '') or '',
                            'fuel_consumed': self._format_decimal(
                                getattr(sample_machine, 'fuel_consumed', zero_decimal) or zero_decimal,
                                zero_decimal,
                            ),
                        },
                        flags=[],
                        data_source='activity_machine',
                        status=self._card_status(has_data=bool(sample_machine and machine_hours > zero_decimal)),
                        policy={'backend_costing_only': True},
                        source_refs=['activity.machine_details', 'activity.asset'],
                    )
                )
            elif card_key == 'fuel':
                fuel_consumed = getattr(sample_machine, 'fuel_consumed', zero_decimal) or zero_decimal
                stack.append(
                    self._build_card_entry(
                        card_key=card_key,
                        order=order_index.get(card_key, 0),
                        mode_visibility=mode_visibility,
                        metrics={
                            'fuel_consumed': self._format_decimal(fuel_consumed, zero_decimal),
                            'inventory_linked': bool(
                                contract.get('financial_profile', {}).get('inventory_linked')
                            ),
                            'reconciliation_posture': 'governed_trace'
                            if policy_snapshot.get('mode') == FarmSettings.MODE_STRICT
                            else 'risk_posture_only',
                        },
                        flags=['budget_overrun'] if fuel_consumed > zero_decimal and Decimal(materials_metrics['cost_variance']) > zero_decimal else [],
                        data_source='activity_machine',
                        status=self._card_status(has_data=bool(sample_machine and fuel_consumed > zero_decimal)),
                        policy={
                            'strict_detail_only': policy_snapshot.get('mode') == FarmSettings.MODE_STRICT,
                            'cost_display_mode': cost_display_mode,
                        },
                        source_refs=['activity.machine_details', 'activity.items'],
                    )
                )
            elif card_key == 'perennial':
                tree_delta = sample_activity.tree_count_delta if sample_activity else 0
                stack.append(
                    self._build_card_entry(
                        card_key=card_key,
                        order=order_index.get(card_key, 0),
                        mode_visibility=mode_visibility,
                        metrics={
                            'tree_count_delta': tree_delta,
                            'activity_tree_count': getattr(sample_activity, 'activity_tree_count', None),
                        },
                        flags=['open_variance'] if tree_delta < 0 else [],
                        data_source='activity',
                        status=self._card_status(has_data=bool(tree_delta), risk=tree_delta < 0),
                        policy={'negative_delta_creates_variance': True},
                        source_refs=['activity', 'variance_alert'],
                    )
                )
            elif card_key == 'harvest':
                harvest_qty = getattr(sample_harvest, 'harvest_quantity', zero_decimal) or zero_decimal
                
                # [AGRI-GUARDIAN] Fetch available products for this crop context
                product_selection = []
                if task and task.crop_id:
                    from smart_agri.core.models import CropProduct
                    products = CropProduct.objects.filter(crop_id=task.crop_id, deleted_at__isnull=True)
                    product_selection = [{'id': p.id, 'name': p.name, 'uom': p.uom} for p in products]

                stack.append(
                    self._build_card_entry(
                        card_key=card_key,
                        order=order_index.get(card_key, 0),
                        mode_visibility=mode_visibility,
                        metrics={
                            'harvest_quantity': self._format_decimal(harvest_qty, zero_decimal),
                            'uom': getattr(sample_harvest, 'uom', None),
                            'available_products': product_selection,
                        },
                        flags=[],
                        data_source='activity_harvest',
                        status=self._card_status(has_data=bool(sample_harvest and harvest_qty > zero_decimal)),
                        source_refs=['activity.harvest_details'],
                    )
                )
            elif card_key == 'control':
                stack.append(
                    self._build_card_entry(
                        card_key=card_key,
                        order=order_index.get(card_key, 0),
                        mode_visibility=mode_visibility,
                        metrics=control_metrics,
                        flags=['critical_control'] if control_metrics.get('critical_logs', 0) > 0 else [],
                        data_source='daily_log',
                        status=self._card_status(
                            has_data=control_metrics.get('total_logs', 0) > 0,
                            critical=control_metrics.get('critical_logs', 0) > 0,
                        ),
                        policy={'read_only': True},
                        source_refs=['daily_log'],
                    )
                )
            elif card_key == 'variance':
                variance_breakdown = (
                    contract.get('variance_rules', {}).get('categories', {})
                    if isinstance(contract.get('variance_rules', {}), dict)
                    else {}
                )
                stack.append(
                    self._build_card_entry(
                        card_key=card_key,
                        order=order_index.get(card_key, 0),
                        mode_visibility=mode_visibility,
                        metrics={
                            **variance_metrics,
                            'categories': variance_breakdown,
                        },
                        flags=['open_variance'] if variance_metrics.get('open_alerts', 0) > 0 else [],
                        data_source='variance_alert',
                        status=self._card_status(
                            has_data=variance_metrics.get('total_alerts', 0) > 0,
                            risk=variance_metrics.get('open_alerts', 0) > 0,
                        ),
                        policy={'read_only': True, 'per_card_classification': True},
                        source_refs=['variance_alert', 'task_contract_snapshot.variance_rules'],
                    )
                )
            elif card_key == 'financial_trace':
                metrics = {
                    'entries_count': ledger_metrics.get('entries_count', 0),
                    'cost_display_mode': cost_display_mode,
                }
                if show_summary_amounts:
                    metrics.update(
                        {
                            'debit_total': ledger_metrics.get('debit_total'),
                            'credit_total': ledger_metrics.get('credit_total'),
                        }
                    )
                stack.append(
                    self._build_card_entry(
                        card_key=card_key,
                        order=order_index.get(card_key, 0),
                        mode_visibility=mode_visibility,
                        metrics=metrics,
                        flags=[],
                        data_source='financial_ledger',
                        status=self._card_status(has_data=ledger_metrics.get('entries_count', 0) > 0),
                        policy={
                            'read_only': True,
                            'strict_detail_only': True,
                            'cost_display_mode': cost_display_mode,
                            'visibility_level': visibility_level,
                        },
                        source_refs=['financial_ledger'],
                    )
                )

        return sorted(stack, key=lambda entry: entry['order'])
    
    def list(self, request):
        from smart_agri.core.models.activity import Activity
        from smart_agri.core.models.log import DailyLog
        from smart_agri.core.models.report import VarianceAlert
        from smart_agri.finance.models import FinancialLedger

        farm_id = request.query_params.get('farm_id')
        crop_id = request.query_params.get('crop_id') or request.query_params.get('crop')
        task_id = request.query_params.get('task_id') or request.query_params.get('task')
        crop_plan_id = request.query_params.get('crop_plan_id') or request.query_params.get('crop_plan')
        target_date = parse_date(request.query_params.get('date')) if request.query_params.get('date') else timezone.localdate()
        location_ids = self._parse_csv_ids(
            request.query_params.get('location_ids')
            or request.query_params.get('location_id')
            or request.query_params.get('locations')
        )
        user = request.user
        accessible_farms = user_farm_ids(user)
        zero_decimal = Decimal("0.0000")

        target_farms = list(accessible_farms)
        if farm_id:
            fids = [int(x) for x in str(farm_id).split(',') if x.strip().isdigit()]
            target_farms = [f for f in fids if f in accessible_farms or user.is_superuser]
            if not target_farms:
                raise PermissionDenied("لا تملك صلاحية الوصول إلى هذه المزرعة.")
        elif not user.is_superuser:
            if not target_farms:
                return Response([])

        qs = (
            Task.objects.filter(
                deleted_at__isnull=True,
                crop__farm_links__farm_id__in=target_farms,
                crop__deleted_at__isnull=True,
            )
            .select_related('crop')
            .order_by('crop_id', 'stage', 'name')
            .distinct()
        )
        if crop_id and str(crop_id).isdigit():
            qs = qs.filter(crop_id=int(crop_id))
        if task_id and str(task_id).isdigit():
            qs = qs.filter(id=int(task_id))

        cards_by_crop = {}
        for task in qs:
            crop = task.crop
            if not crop:
                continue
            card = cards_by_crop.setdefault(
                crop.id,
                {
                    'crop': {'id': crop.id, 'name': crop.name},
                    'metrics': {
                        'total': 0,
                        'machinery': 0,
                        'well': 0,
                        'area': 0,
                        'tree_count': 0,
                        'asset_types': [],
                        'asset_tasks_missing_type': 0,
                    },
                    'stage_groups': {},
                },
            )

            card['metrics']['total'] += 1
            if task.requires_machinery:
                card['metrics']['machinery'] += 1
            if task.requires_well:
                card['metrics']['well'] += 1
            if task.requires_area:
                card['metrics']['area'] += 1
            if task.requires_tree_count:
                card['metrics']['tree_count'] += 1
            if task.is_asset_task:
                if task.asset_type:
                    if task.asset_type not in card['metrics']['asset_types']:
                        card['metrics']['asset_types'].append(task.asset_type)
                else:
                    card['metrics']['asset_tasks_missing_type'] += 1

            stage = task.stage or 'General'
            stage_entry = card['stage_groups'].setdefault(
                stage, {'stage': stage, 'count': 0, 'services': []}
            )
            stage_entry['count'] += 1
            stage_entry['services'].append({'id': task.id, 'name': task.name})

        policy_snapshot = self._resolve_policy_snapshot(target_farms)
        payload = []
        for card in cards_by_crop.values():
            crop_id = card['crop']['id']
            selected_task = None
            if task_id and str(task_id).isdigit():
                selected_task = Task.objects.filter(id=int(task_id), crop_id=crop_id).first()

            activity_qs = Activity.objects.filter(
                deleted_at__isnull=True,
                log__farm_id__in=target_farms,
                crop_id=crop_id,
            )
            log_qs = DailyLog.objects.filter(
                deleted_at__isnull=True,
                farm_id__in=target_farms,
                activities__crop_id=crop_id,
            ).distinct()
            variance_qs = VarianceAlert.objects.filter(
                farm_id__in=target_farms,
                daily_log__in=log_qs,
            )
            ledger_qs = (
                FinancialLedger.objects.filter(farm_id__in=target_farms)
                .filter(Q(activity__crop_id=crop_id) | Q(crop_plan__crop_id=crop_id))
                .distinct()
            )
            selected_plan = self._resolve_crop_plan(
                crop_id=crop_id,
                target_farms=target_farms,
                explicit_plan_id=int(crop_plan_id) if crop_plan_id and str(crop_plan_id).isdigit() else None,
                target_date=target_date,
                location_ids=location_ids,
            )
            selected_activity_qs = Activity.objects.none()
            sample_activity = None
            if selected_task:
                selected_activity_qs = (
                    Activity.objects.filter(
                        deleted_at__isnull=True,
                        log__farm_id__in=target_farms,
                        crop_id=crop_id,
                        task_id=selected_task.id,
                    )
                    .select_related('log', 'asset', 'machine_details', 'irrigation_details', 'harvest_details')
                    .prefetch_related('items__item', 'employee_details')
                )
                if selected_plan:
                    selected_activity_qs = selected_activity_qs.filter(crop_plan=selected_plan)
                if target_date:
                    selected_activity_qs = selected_activity_qs.filter(log__log_date=target_date)
                sample_activity = selected_activity_qs.order_by('-log__log_date', '-id').first()

            achievement = activity_qs.aggregate(
                total_activities=Count('id'),
                total_cost=Coalesce(Sum('cost_total'), Value(zero_decimal)),
                latest_log_date=Max('log__log_date'),
            )
            controls = log_qs.aggregate(
                total_logs=Count('id'),
                approved_logs=Count('id', filter=Q(status='APPROVED')),
                submitted_logs=Count('id', filter=Q(status='SUBMITTED')),
                draft_logs=Count('id', filter=Q(status='DRAFT')),
                rejected_logs=Count('id', filter=Q(status='REJECTED')),
                critical_logs=Count('id', filter=Q(variance_status='CRITICAL')),
                warning_logs=Count('id', filter=Q(variance_status='WARNING')),
            )
            variances = variance_qs.aggregate(
                total_alerts=Count('id'),
                open_alerts=Count(
                    'id',
                    filter=Q(
                        status__in=[
                            VarianceAlert.ALERT_STATUS_UNINVESTIGATED,
                            VarianceAlert.ALERT_STATUS_UNDER_REVIEW,
                        ]
                    ),
                ),
                resolved_alerts=Count(
                    'id',
                    filter=Q(
                        status__in=[
                            VarianceAlert.ALERT_STATUS_RESOLVED_JUSTIFIED,
                            VarianceAlert.ALERT_STATUS_RESOLVED_PENALIZED,
                        ]
                    ),
                ),
                total_variance=Coalesce(Sum('variance_amount'), Value(zero_decimal)),
                latest_alert_at=Max('created_at'),
            )
            ledger = ledger_qs.aggregate(
                entries_count=Count('id'),
                debit_total=Coalesce(Sum('debit'), Value(zero_decimal)),
                credit_total=Coalesce(Sum('credit'), Value(zero_decimal)),
                latest_entry_at=Max('created_at'),
            )
            total_logs = controls['total_logs'] or 0
            approved_logs = controls['approved_logs'] or 0
            completion_rate = round((approved_logs / total_logs) * 100, 2) if total_logs else 0

            card['metrics']['asset_types'] = sorted(card['metrics']['asset_types'])
            card['stage_groups'] = list(card['stage_groups'].values())

            control_metrics_dict = {
                'total_logs': total_logs,
                'submitted_logs': controls['submitted_logs'] or 0,
                'draft_logs': controls['draft_logs'] or 0,
                'rejected_logs': controls['rejected_logs'] or 0,
                'critical_logs': controls['critical_logs'] or 0,
                'warning_logs': controls['warning_logs'] or 0,
            }
            variance_metrics_dict = {
                'total_alerts': variances['total_alerts'] or 0,
                'open_alerts': variances['open_alerts'] or 0,
                'resolved_alerts': variances['resolved_alerts'] or 0,
                'total_variance': self._format_decimal(variances['total_variance'] or zero_decimal, zero_decimal),
                'latest_alert_at': variances['latest_alert_at'],
            }
            ledger_metrics_dict = {
                'entries_count': ledger['entries_count'] or 0,
                'debit_total': self._format_decimal(ledger['debit_total'] or zero_decimal, zero_decimal),
                'credit_total': self._format_decimal(ledger['credit_total'] or zero_decimal, zero_decimal),
                'latest_entry_at': ledger['latest_entry_at'],
            }
            card['visibility_level'] = policy_snapshot['visibility_level']
            card['cost_display_mode'] = policy_snapshot['cost_visibility']
            card['policy_snapshot'] = policy_snapshot
            
            health_flags = []
            if selected_task and not selected_plan:
                health_flags.append('missing_active_plan')
            if variance_metrics_dict['open_alerts'] > 0:
                health_flags.append('open_variance')
            if control_metrics_dict['critical_logs'] > 0:
                health_flags.append('critical_control')
                
            card['smart_card_stack'] = self._build_smart_card_stack(
                task=selected_task,
                activity_qs=selected_activity_qs,
                sample_activity=sample_activity,
                policy_snapshot=policy_snapshot,
                selected_plan=selected_plan,
                target_date=target_date,
                location_ids=location_ids,
                control_metrics=control_metrics_dict,
                variance_metrics=variance_metrics_dict,
                ledger_metrics=ledger_metrics_dict,
                health_flags=health_flags,
                zero_decimal=zero_decimal,
            )
            payload.append(card)
        return Response(payload)


class CropRecipeViewSet(AuditedModelViewSet):
    """
    [AGRI-GUARDIAN] Axis 6 / Protocol III Validation:
    Enforces BOM (Bill of Materials) recipes for planned agricultural operations.
    """
    serializer_class = CropRecipeSerializer
    model_name = "CropRecipe"

    def get_queryset(self):
        qs = CropRecipe.objects.select_related('crop').prefetch_related(
            'materials', 'materials__item',
            'tasks', 'tasks__task'
        ).all()
        # Recipes are template-level, usually farm-agnostic but handled per-tenant if required.
        return qs.order_by('-created_at')

    def _assert_can_mutate(self, instance):
        user = getattr(self.request, 'user', None)
        if not user or not user.is_authenticated:
            raise PermissionDenied("يجب تسجيل الدخول.")
        if not (user.is_superuser or user.has_perm('core.change_croprecipe')):
            raise PermissionDenied("لا تملك صلاحية تعديل الوصفات الزراعية.")


class CropRecipeMaterialViewSet(AuditedModelViewSet):
    serializer_class = CropRecipeMaterialSerializer
    model_name = "CropRecipeMaterial"

    def get_queryset(self):
        return CropRecipeMaterial.objects.select_related('recipe', 'item').all().order_by('id')

    def _assert_can_mutate(self, instance):
        user = getattr(self.request, 'user', None)
        if not user or not user.is_authenticated:
            raise PermissionDenied("يجب تسجيل الدخول.")
        if not (user.is_superuser or user.has_perm('core.change_croprecipematerial')):
            raise PermissionDenied("لا تملك صلاحية تعديل مواد الوصفة.")


class CropRecipeTaskViewSet(AuditedModelViewSet):
    serializer_class = CropRecipeTaskSerializer
    model_name = "CropRecipeTask"

    def get_queryset(self):
        return CropRecipeTask.objects.select_related('recipe', 'task').all().order_by('days_offset', 'id')

    def _assert_can_mutate(self, instance):
        user = getattr(self.request, 'user', None)
        if not user or not user.is_authenticated:
            raise PermissionDenied("يجب تسجيل الدخول.")
        if not (user.is_superuser or user.has_perm('core.change_croprecipetask')):
            raise PermissionDenied("لا تملك صلاحية تعديل مهام الوصفة.")
