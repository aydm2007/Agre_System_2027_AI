"""
Farm ViewSets
"""
from typing import Any
from django.db import IntegrityError
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from django.db.models import Count
from rest_framework import viewsets, status
from rest_framework.authentication import SessionAuthentication
try:
    from rest_framework_simplejwt.authentication import JWTAuthentication
except (ImportError, RuntimeError):  # pragma: no cover - optional dependency guard
    JWTAuthentication = None
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError

from smart_agri.core.models import Farm, Location, Asset, LocationWell, LocationIrrigationPolicy
from smart_agri.core.api.serializers import (
    FarmSerializer, LocationSerializer, AssetSerializer, LocationWellSerializer, LocationIrrigationPolicySerializer
)
from smart_agri.core.api.permissions import (
    user_farm_ids, 
    _ensure_user_has_farm_access, 
    FarmScopedPermission,
    _limit_queryset_to_user_farms,
    user_has_sector_finance_authority,
)
from smart_agri.accounts.models import FarmMembership
from .base import AuditedModelViewSet, IdempotentCreateMixin

LOCATION_WELL_DUPLICATE_MESSAGE = "تم ربط هذا الموقع بالبئر مسبقًا."


class FarmViewSet(AuditedModelViewSet):
    serializer_class = FarmSerializer
    authentication_classes = [SessionAuthentication] + ([JWTAuthentication] if JWTAuthentication else [])
    
    def get_queryset(self) -> Any:
        ids = user_farm_ids(self.request.user)
        base = Farm.objects.all().filter(deleted_at__isnull=True).order_by("name", "id")
        return base.filter(id__in=ids) if not self.request.user.is_superuser else base

    def perform_create(self, serializer):
        farm = serializer.save()
        user = self.request.user
        if user and user.is_authenticated:
            # Grant access to creator
            default_role = "Admin" if (user.is_superuser or user.groups.filter(name="Admin").exists()) else "Manager"
            FarmMembership.objects.get_or_create(
                user=user,
                farm=farm,
                defaults={"role": default_role},
            )


class LocationViewSet(AuditedModelViewSet):
    serializer_class = LocationSerializer
    
    def get_queryset(self) -> Any:
        ids = user_farm_ids(self.request.user)
        qs = Location.objects.all().filter(deleted_at__isnull=True)
        farm_id = self.request.query_params.get('farm_id') if hasattr(self.request, 'query_params') else None
        if farm_id:
            qs = qs.filter(farm_id=farm_id)
        return qs.filter(farm_id__in=ids) if not self.request.user.is_superuser else qs


class AssetViewSet(AuditedModelViewSet):
    serializer_class = AssetSerializer
    
    def get_queryset(self) -> Any:
        ids = user_farm_ids(self.request.user)
        qs = Asset.objects.all().filter(deleted_at__isnull=True)
        farm_id = self.request.query_params.get('farm_id') if hasattr(self.request, 'query_params') else None
        if farm_id:
            qs = qs.filter(farm_id=farm_id)
        category = self.request.query_params.get('category') if hasattr(self.request, 'query_params') else None
        if category:
            qs = qs.filter(category__iexact=category)
        
        # [AGRI-GUARDIAN] Support finer granularity for Task-Resource mapping
        asset_type = self.request.query_params.get('asset_type') if hasattr(self.request, 'query_params') else None
        if asset_type:
             qs = qs.filter(asset_type__iexact=asset_type)
        
        return qs.filter(farm_id__in=ids) if not self.request.user.is_superuser else qs

    @action(detail=False, methods=['post'], url_path='run-depreciation')
    def run_depreciation(self, request):
        """
        [Financial Closing] Trigger Monthly Depreciation.
        Admin Only.
        """
        key, error_response = self._enforce_action_idempotency(request)
        if error_response:
            return error_response
        if not request.user.is_superuser:
             # Or check for specific financial permission
             raise PermissionDenied("فقط المسؤولون يمكنهم تنفيذ الإهلاك.")
             
        try:
             from smart_agri.core.services.asset_service import AssetService
             count = AssetService.run_monthly_depreciation(request.user)
             response = Response({'status': 'complete', 'processed_count': count})
             self._commit_action_idempotency(request, key, object_id=f"depreciation:{count}", response=response)
             return response
        except (ValidationError, OperationalError, PermissionDenied) as e:
             return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


    @action(detail=True, methods=['post'], url_path='capitalize')
    def capitalize(self, request, pk=None):
        """
        [Fixed Assets] Capitalize an asset (IAS16-like).
        Requires finance authority.
        """
        if not (request.user.is_superuser or user_has_sector_finance_authority(request.user)):
            raise PermissionDenied('صلاحية مالية مطلوبة لرسملة الأصول.')
        key, error_response = self._enforce_action_idempotency(request)
        if error_response:
            return error_response
        data = request.data or {}
        reason = data.get('reason') or ''
        ref_id = data.get('ref_id') or ''
        effective_date = parse_date(data.get('effective_date')) if data.get('effective_date') else None
        funding_account = data.get('funding_account')
        value = data.get('capitalized_value')
        try:
            from smart_agri.core.services.fixed_asset_lifecycle_service import FixedAssetLifecycleService
            result = FixedAssetLifecycleService.capitalize_asset(
                user=request.user,
                asset_id=int(pk),
                capitalized_value=value,
                effective_date=effective_date,
                funding_account=funding_account,
                reason=reason,
                ref_id=ref_id,
            )
            response = Response(result)
            self._commit_action_idempotency(request, key, object_id=f"asset:{pk}:capitalize", response=response)
            return response
        except (ValueError, TypeError, ValidationError, DjangoValidationError, PermissionDenied) as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='dispose')
    def dispose(self, request, pk=None):
        """
        [Fixed Assets] Dispose an asset with proceeds and auto-balance gain/loss.
        Requires finance authority.
        """
        if not (request.user.is_superuser or user_has_sector_finance_authority(request.user)):
            raise PermissionDenied('صلاحية مالية مطلوبة لاستبعاد الأصول.')
        key, error_response = self._enforce_action_idempotency(request)
        if error_response:
            return error_response
        data = request.data or {}
        reason = data.get('reason') or ''
        ref_id = data.get('ref_id') or ''
        effective_date = parse_date(data.get('effective_date')) if data.get('effective_date') else None
        proceeds_account = data.get('proceeds_account')
        proceeds = data.get('proceeds_value')
        try:
            from smart_agri.core.services.fixed_asset_lifecycle_service import FixedAssetLifecycleService
            result = FixedAssetLifecycleService.dispose_asset(
                user=request.user,
                asset_id=int(pk),
                proceeds_value=proceeds,
                effective_date=effective_date,
                proceeds_account=proceeds_account,
                reason=reason,
                ref_id=ref_id,
            )
            response = Response(result)
            self._commit_action_idempotency(request, key, object_id=f"asset:{pk}:dispose", response=response)
            return response
        except (ValueError, TypeError, ValidationError, DjangoValidationError, PermissionDenied) as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='tree-snapshot')
    def tree_snapshot(self, request):
        """
        [Agri-Guardian] Return Tree Inventory Snapshot for a Location.
        Used for Offline Intelligence & Service Row Validation.
        """
        location_id = request.query_params.get('location_id')
        if not location_id:
             return Response([])

        from smart_agri.core.models.tree import LocationTreeStock
        
        # Security: Filter by user access (already implicit via Location check usually, but strict here)
        # We assume if they have access to the location, they can see the trees.
        
        stocks = LocationTreeStock.objects.filter(
            location_id=location_id
        ).select_related('crop_variety').only(
            'crop_variety__id', 'crop_variety__name', 'current_tree_count'
        )
        
        data = [
            {
                'variety_id': s.crop_variety.id,
                'variety_name': s.crop_variety.name,
                'count': s.current_tree_count
            }
            for s in stocks
        ]
        return Response(data)


class LocationWellViewSet(AuditedModelViewSet):
    queryset = LocationWell.objects.select_related('location__farm', 'asset__farm').all()
    serializer_class = LocationWellSerializer

    def get_queryset(self):
        # Farm scoping here is relation-based (location__farm_id), not a direct LocationWell.farm field.
        qs = super().get_queryset().filter(
            deleted_at__isnull=True, 
            asset__deleted_at__isnull=True,
            location__deleted_at__isnull=True
        )
        qs = _limit_queryset_to_user_farms(qs, self.request.user, 'location__farm_id__in')
        params = getattr(self.request, 'query_params', {})
        farm_id = params.get('farm') or params.get('farm_id')
        location_id = params.get('location') or params.get('location_id')
        asset_id = params.get('asset') or params.get('asset_id')
        status_value = params.get('status') or params.get('status_id')
        if farm_id:
            qs = qs.filter(location__farm_id=farm_id)
        if location_id:
            qs = qs.filter(location_id=location_id)
        if asset_id:
            qs = qs.filter(asset_id=asset_id)
        if status_value:
            qs = qs.filter(status=status_value)
        return qs

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs.get(lookup_url_kwarg)
        base_queryset = LocationWell.objects.select_related('location__farm', 'asset__farm')
        obj = get_object_or_404(base_queryset, **{self.lookup_field: lookup_value})
        _ensure_user_has_farm_access(self.request.user, obj.location.farm_id)
        self.check_object_permissions(self.request, obj)
        return obj

    def _ensure_same_farm(self, location, asset):
        if location.farm_id != asset.farm_id:
            raise PermissionDenied('يجب أن يكون البئر والموقع في نفس المزرعة.')
        if asset.category != 'Well':
            raise PermissionDenied('الأصل المختار ليس بئراً.')
        _ensure_user_has_farm_access(self.request.user, location.farm_id)

    def perform_create(self, serializer):
        location = serializer.validated_data.get('location')
        asset = serializer.validated_data.get('asset')
        self._ensure_same_farm(location, asset)
        try:
            serializer.save()
        except (IntegrityError, DjangoValidationError):
            raise ValidationError({'detail': LOCATION_WELL_DUPLICATE_MESSAGE})

    def perform_update(self, serializer):
        location = serializer.validated_data.get('location', serializer.instance.location)
        asset = serializer.validated_data.get('asset', serializer.instance.asset)
        self._ensure_same_farm(location, asset)
        try:
            serializer.save()
        except (IntegrityError, DjangoValidationError):
            raise ValidationError({'detail': LOCATION_WELL_DUPLICATE_MESSAGE})

    def perform_destroy(self, instance):
        _ensure_user_has_farm_access(self.request.user, instance.location.farm_id)
        super().perform_destroy(instance)

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except (IntegrityError, DjangoValidationError):
            raise ValidationError({'detail': LOCATION_WELL_DUPLICATE_MESSAGE})

    @action(detail=False, methods=['get'])
    def summary(self, request, *args, **kwargs):
        try:
            # [Agri-Guardian] Nuclear Fix: Bypass get_queryset()
            
            from smart_agri.core.models import LocationWell
            from smart_agri.core.constants import AssetStatus
            from smart_agri.core.api.permissions import _ensure_user_has_farm_access
            
            farm_id = request.query_params.get('farm_id') or request.query_params.get('farm')
            if not farm_id:
                return Response({'detail': "معرف المزرعة مطلوب."}, status=400)
                
            # Security Check
            _ensure_user_has_farm_access(request.user, farm_id)
            
            # Clean Query - No Select Related, No Default Ordering
            qs = LocationWell.objects.filter(
                location__farm_id=farm_id, 
                deleted_at__isnull=True,
                asset__deleted_at__isnull=True,
                location__deleted_at__isnull=True
            ).values(
                'id', 
                'status', 
                'location_id', 
                'location__name'
            ).order_by()
            
            # Convert to list immediately to execute SQL
            raw_data = list(qs)
            
            # Python Aggregation
            from collections import Counter
            status_counts = Counter()
            location_counts = Counter()
            location_names = {}
            
            for row in raw_data:
                status = row['status']
                loc_id = row['location_id']
                
                status_counts[status] += 1
                location_counts[loc_id] += 1
                
                if loc_id not in location_names:
                    location_names[loc_id] = row['location__name'] or f"موقع #{loc_id}"

            # Format Response
            label_map = dict(AssetStatus.choices)
            by_status = [
                {
                    'status': code,
                    'label': label_map.get(code, code.title()),
                    'count': status_counts[code]
                }
                for code, _ in AssetStatus.choices
            ]
            
            by_location = [
                {
                    'location_id': loc_id,
                    'location_name': location_names.get(loc_id, "غير معروف"),
                    'well_count': count
                }
                for loc_id, count in location_counts.items()
            ]
            
            by_location.sort(key=lambda x: (-x['well_count'], x['location_name']))
            
            payload = {
                'total': len(raw_data),
                'by_status': by_status,
                'by_location': by_location,
            }
            return Response(payload)

        except (ValidationError, OperationalError, PermissionDenied) as e:
            import traceback
            traceback.print_exc()
            return Response(
                {'detail': f"خطأ في ملخص الآبار: {str(e)}"}, 
                status=400
            )

class LocationIrrigationPolicyViewSet(AuditedModelViewSet):
    serializer_class = LocationIrrigationPolicySerializer
    permission_classes = [FarmScopedPermission]
    queryset = LocationIrrigationPolicy.objects.select_related("location__farm", "approved_by").all()

    def get_queryset(self):
        qs = super().get_queryset().filter(deleted_at__isnull=True)
        if not self.request.user.is_superuser:
            qs = _limit_queryset_to_user_farms(qs, self.request.user, "location__farm_id__in")
        farm_id = self.request.query_params.get("farm") or self.request.query_params.get("farm_id")
        location_id = self.request.query_params.get("location") or self.request.query_params.get("location_id")
        active = self.request.query_params.get("is_active")
        if farm_id:
            qs = qs.filter(location__farm_id=farm_id)
        if location_id:
            qs = qs.filter(location_id=location_id)
        if active is not None:
            qs = qs.filter(is_active=str(active).lower() == "true")
        return qs.order_by("location_id", "-created_at")

    def perform_create(self, serializer):
        if not user_has_sector_finance_authority(self.request.user):
            raise PermissionDenied("Only sector finance authority can create irrigation policies.")
        location = serializer.validated_data.get("location")
        _ensure_user_has_farm_access(self.request.user, location.farm_id)
        serializer.save(approved_by=self.request.user)

    def perform_update(self, serializer):
        if not user_has_sector_finance_authority(self.request.user):
            raise PermissionDenied("Only sector finance authority can update irrigation policies.")
        location = serializer.validated_data.get("location", serializer.instance.location)
        _ensure_user_has_farm_access(self.request.user, location.farm_id)
        serializer.save(approved_by=self.request.user)
