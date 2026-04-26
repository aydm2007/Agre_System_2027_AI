"""
Inventory ViewSets
"""
import logging
from typing import Any, List, Optional
from decimal import Decimal
from django.db import transaction
from django.db import DatabaseError, IntegrityError
from django.db.models import Sum, Count, Q, Max, F
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import viewsets, permissions, status, mixins
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError as DRFValidationError

from smart_agri.core.models import (
    Item, ItemInventory, StockMovement, 
    # MaterialCatalog, HarvestProductCatalog, 
    HarvestLot, Crop, FarmCrop, 
    Location, CropMaterial, CropProduct, Farm, Unit,
    LocationTreeStock, TreeServiceCoverage, TreeStockEvent
)
from smart_agri.core.api.serializers import (
    ItemSerializer, ItemInventorySerializer, StockMovementSerializer,
    HarvestLotSerializer, CropProductSerializer, UnitSerializer,
    CropProductUnitSerializer,
    LocationTreeStockSerializer, TreeStockEventSerializer,
    ManualTreeAdjustmentSerializer, TreeProductivityRefreshSerializer,
    MassCasualtyWriteoffRequestSerializer
)
from smart_agri.core.api.permissions import (
    user_farm_ids, 
    _ensure_user_has_farm_access, 
    _limit_queryset_to_user_farms,
    FarmScopedPermission
)
from smart_agri.core.api.utils import (
    _coerce_int,
    _strict_decimal,
    _csv_response,
    _coerce_int_list,
    _parse_bool,
)
from smart_agri.core.api.permissions import StrictErpOnlyPermission
from .base import AuditedModelViewSet
from django.core.exceptions import ValidationError as DjangoValidationError

# Attempt to import service, assume standard location or check imports
try:
    from smart_agri.core.services import TreeInventoryService, MassCasualtyWriteoffService
except ImportError:
    TreeInventoryService = None
    MassCasualtyWriteoffService = None

logger = logging.getLogger(__name__)


class ItemViewSet(AuditedModelViewSet):
    # Depending on where ItemViewSet was defined, assuming standard structure
    queryset = Item.objects.filter(deleted_at__isnull=True).order_by("group", "name")
    serializer_class = ItemSerializer
    permission_classes = [permissions.IsAuthenticated, FarmScopedPermission, StrictErpOnlyPermission]
    
    def get_queryset(self):
        qs = super().get_queryset()
        group = self.request.query_params.get('group')
        search = self.request.query_params.get('q')
        crop_id = self.request.query_params.get('crop') or self.request.query_params.get('crop_id')
        if group:
            if ',' in group:
                qs = qs.filter(group__in=[g.strip() for g in group.split(',')])
            else:
                qs = qs.filter(group=group)
                
        exclude_group = self.request.query_params.get('exclude_group')
        if exclude_group:
            if ',' in exclude_group:
                qs = qs.exclude(group__in=[g.strip() for g in exclude_group.split(',')])
            else:
                qs = qs.exclude(group=exclude_group)
        if crop_id:
            crop_item_ids = CropProduct.objects.filter(
                crop_id=crop_id,
                deleted_at__isnull=True,
            ).values_list('item_id', flat=True)
            qs = qs.filter(id__in=crop_item_ids)
        if search:
            qs = qs.filter(name__icontains=search)
        return qs

class ItemInventoryViewSet(AuditedModelViewSet):
    queryset = ItemInventory.objects.all().select_related('farm', 'item', 'item__unit', 'location')
    serializer_class = ItemInventorySerializer
    model_name = "ItemInventory"

    def get_queryset(self):
        qs = super().get_queryset()
        qs = _limit_queryset_to_user_farms(qs, self.request.user, 'farm_id__in')
        farm_id = self.request.query_params.get('farm') or self.request.query_params.get('farm_id')
        item_id = self.request.query_params.get('item') or self.request.query_params.get('item_id')
        location_id = self.request.query_params.get('location') or self.request.query_params.get('location_id')
        if farm_id:
            qs = qs.filter(farm_id=farm_id)
        if item_id:
            qs = qs.filter(item_id=item_id)
        if location_id:
            if str(location_id).lower() == 'null':
                qs = qs.filter(location_id__isnull=True)
            else:
                qs = qs.filter(location_id=location_id)
                
        group = self.request.query_params.get('group')
        if group:
            if ',' in group:
                qs = qs.filter(item__group__in=[g.strip() for g in group.split(',')])
            else:
                qs = qs.filter(item__group=group)
                
        exclude_group = self.request.query_params.get('exclude_group')
        if exclude_group:
            if ',' in exclude_group:
                qs = qs.exclude(item__group__in=[g.strip() for g in exclude_group.split(',')])
            else:
                qs = qs.exclude(item__group=exclude_group)
                
        return qs

    def perform_create(self, serializer):
        instance = serializer.save()
        _ensure_user_has_farm_access(self.request.user, instance.farm_id)
        return instance

    def perform_update(self, serializer):
        instance = serializer.save()
        _ensure_user_has_farm_access(self.request.user, instance.farm_id)
        return instance

    @action(detail=False, methods=['post'], url_path='adjust')
    def adjust(self, request):
        key, error_response = self._enforce_action_idempotency(request)
        if error_response:
            return error_response
        farm_id = request.data.get('farm_id')
        item_id = request.data.get('item_id')
        qty_change = self._require_decimal(request.data.get('qty_change'), field_name='qty_change')
        location_id = request.data.get('location_id')  # Optional
        notes = request.data.get('notes', '')

        if not farm_id or not item_id:
            return Response({'detail': 'Farm and Item are required.'}, status=status.HTTP_400_BAD_REQUEST)

        _ensure_user_has_farm_access(request.user, farm_id)

        _ensure_user_has_farm_access(request.user, farm_id)

        try:
             # CORE FIX: Use Service Layer for adjustments (Single Source of Truth)
             from smart_agri.core.services.inventory_service import InventoryService
             from smart_agri.core.models import Farm, Item, Location
             
             farm = Farm.objects.get(pk=farm_id)
             item = Item.objects.get(pk=item_id)
             location = Location.objects.get(pk=location_id) if location_id else None
             
             # Atomic Service Call
             InventoryService.record_movement(
                 farm=farm,
                 item=item,
                 qty_delta=qty_change,
                 location=location,
                 ref_type='manual_adjustment',
                 ref_id=f"user_{request.user.id}",
                 note=notes,
                 # NOTE: batch_number support available when UI is ready
             )
             
             # Fetch updated record for response
             inventory = ItemInventory.objects.get(
                 farm=farm, 
                 item=item, 
                 location=location
             )
             response = Response(ItemInventorySerializer(inventory).data)
             self._commit_action_idempotency(request, key, object_id=str(inventory.id), response=response)
             return response
             
        except (Farm.DoesNotExist, Item.DoesNotExist, Location.DoesNotExist):
             return Response({'detail': 'Resource not found.'}, status=status.HTTP_404_NOT_FOUND)
        except (DjangoValidationError, DRFValidationError):
             raise
        except PermissionDenied:
             raise
        except (IntegrityError, DatabaseError) as exc:
             raise DRFValidationError({'detail': f'Database integrity error: {exc}'})

    @action(detail=False, methods=['post'], url_path='transfer')
    def transfer(self, request):
        """
        [Store Integration] API Endpoint for Stock Transfer.
        """
        key, error_response = self._enforce_action_idempotency(request)
        if error_response:
            return error_response
        farm_id = request.data.get('farm_id')
        item_id = request.data.get('item_id')
        from_loc_id = request.data.get('from_location_id')
        to_loc_id = request.data.get('to_location_id')
        qty = self._require_decimal(request.data.get('qty'), field_name='qty')
        batch_number = request.data.get('batch_number')

        if not all([farm_id, item_id, from_loc_id, to_loc_id, qty]):
             return Response({'detail': 'Missing required fields.'}, status=status.HTTP_400_BAD_REQUEST)

        _ensure_user_has_farm_access(request.user, farm_id)

        try:
             from smart_agri.core.services.inventory_service import InventoryService
             from smart_agri.core.models import Farm, Item, Location
             
             InventoryService.transfer_stock(
                 farm=Farm.objects.get(pk=farm_id),
                 item=Item.objects.get(pk=item_id),
                 from_loc=Location.objects.get(pk=from_loc_id),
                 to_loc=Location.objects.get(pk=to_loc_id),
                 qty=qty,
                 user=request.user,
                 batch_number=batch_number
             )
             response = Response({'status': 'transferred'})
             self._commit_action_idempotency(request, key, object_id=f"{farm_id}:{item_id}", response=response)
             return response
        except (Farm.DoesNotExist, Item.DoesNotExist, Location.DoesNotExist):
             return Response({'detail': 'Resource not found.'}, status=status.HTTP_404_NOT_FOUND)
        except (DjangoValidationError, DRFValidationError):
             raise
        except PermissionDenied:
             raise
        except (IntegrityError, DatabaseError) as exc:
             raise DRFValidationError({'detail': f'Database integrity error: {exc}'})

    @action(detail=False, methods=['post'], url_path='receive')
    def receive(self, request):
        """
        [Procurement Integration] API ID for GRN (Receive Goods).
        Updates Stock & Moving Average Price.
        """
        key, error_response = self._enforce_action_idempotency(request)
        if error_response:
            return error_response
        farm_id = request.data.get('farm_id')
        item_id = request.data.get('item_id')
        location_id = request.data.get('location_id')
        qty = self._require_decimal(request.data.get('qty'), field_name='qty')
        unit_cost = self._require_decimal(request.data.get('unit_cost'), field_name='unit_cost')
        ref_id = request.data.get('ref_id', f"GRN-{timezone.now().timestamp()}")
        batch_number = request.data.get('batch_number')

        _ensure_user_has_farm_access(request.user, farm_id)

        try:
             from smart_agri.core.services.inventory_service import InventoryService
             from smart_agri.core.models import Farm, Item, Location
             
             InventoryService.process_grn(
                 farm=Farm.objects.get(pk=farm_id),
                 item=Item.objects.get(pk=item_id),
                 location=Location.objects.get(pk=location_id),
                 qty=qty,
                 unit_cost=unit_cost,
                 ref_id=ref_id,
                 batch_number=batch_number
             )
             response = Response({'status': 'received'})
             self._commit_action_idempotency(request, key, object_id=f"{farm_id}:{item_id}:{ref_id}", response=response)
             return response
        except (Farm.DoesNotExist, Item.DoesNotExist, Location.DoesNotExist):
             return Response({'detail': 'Resource not found.'}, status=status.HTTP_404_NOT_FOUND)
        except (DjangoValidationError, DRFValidationError):
             raise
        except PermissionDenied:
             raise
        except (IntegrityError, DatabaseError) as exc:
             raise DRFValidationError({'detail': f'Database integrity error: {exc}'})

    def _require_decimal(self, value, *, field_name):
        if value in (None, ""):
            raise DRFValidationError({field_name: "هذه القيمة مطلوبة."})
        if isinstance(value, float):
            raise DRFValidationError({field_name: "استخدام float ممنوع. أرسل القيمة كنص أو Decimal."})
        candidate = _strict_decimal(value)
        if candidate is None:
            raise DRFValidationError({field_name: "قيمة رقمية غير صالحة."})
        return candidate


class StockMovementViewSet(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    queryset = StockMovement.objects.all().order_by('-created_at')
    serializer_class = StockMovementSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = _limit_queryset_to_user_farms(qs, self.request.user, 'farm_id__in')
        farm_id = self.request.query_params.get('farm') or self.request.query_params.get('farm_id')
        item_id = self.request.query_params.get('item') or self.request.query_params.get('item_id')
        if farm_id:
            qs = qs.filter(farm_id=farm_id)
        if item_id:
            qs = qs.filter(item_id=item_id)
        return qs


class HarvestLotViewSet(AuditedModelViewSet):
    queryset = HarvestLot.objects.filter(deleted_at__isnull=True).select_related('farm', 'crop', 'product', 'unit')
    serializer_class = HarvestLotSerializer
    model_name = "HarvestLot"

    def get_queryset(self):
        qs = super().get_queryset()
        qs = _limit_queryset_to_user_farms(qs, self.request.user, 'farm_id__in')
        farm_id = self.request.query_params.get('farm')
        crop_id = self.request.query_params.get('crop')
        product_id = self.request.query_params.get('product')
        if farm_id: qs = qs.filter(farm_id=farm_id)
        if crop_id: qs = qs.filter(crop_id=crop_id)
        if product_id: qs = qs.filter(product_id=product_id)
        return qs

    def perform_create(self, serializer):
        farm = serializer.validated_data.get('farm')
        if farm:
            _ensure_user_has_farm_access(self.request.user, getattr(farm, 'id', getattr(farm, 'pk', None)))
        super().perform_create(serializer)

    def perform_update(self, serializer):
        farm = serializer.validated_data.get('farm') or serializer.instance.farm
        if farm:
            _ensure_user_has_farm_access(self.request.user, getattr(farm, 'id', getattr(farm, 'pk', None)))
        super().perform_update(serializer)


# --- Catalogs (Read Only / Aggregated) ---

class MaterialCatalogViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        farm_id_param = request.query_params.get('farm_id')
        
        target_farm_ids = []
        target_farm_ids = []
        if farm_id_param:
            # [FIX]: Handle CSV or single ID safely
            try:
                # Support single ID logic primarily for this catalog, but tolerate CSV list (take first or filter)
                # If we want to support multiple farms for catalog, we should use __in. 
                # For now, let's just make it crash-proof.
                if ',' in str(farm_id_param):
                     # If CSV provided, we might want to filter by ALL of them if permitted.
                     # But current logic below uses a loop or list. 
                     # Let's collect them all.
                     fids = [int(x) for x in str(farm_id_param).split(',') if x.strip().isdigit()]
                     for fid in fids:
                        _ensure_user_has_farm_access(request.user, fid)
                     target_farm_ids = fids
                else:
                    fid = int(farm_id_param)
                    _ensure_user_has_farm_access(request.user, fid)
                    target_farm_ids = [fid]
            except (ValueError, TypeError, PermissionDenied):
                # If parsing fails or permission denied, return empty or raise
                # Raising 403 or 400 is better than 500.
                pass
        elif not request.user.is_superuser:
            target_farm_ids = user_farm_ids(request.user)
            if not target_farm_ids:
                return Response([])
        
        if target_farm_ids == []: # Explicit empty list means no access
             return Response([])
             
        # [MODIFIED] Added server-side filtering for item and location
        qs = CropMaterial.objects.filter(deleted_at__isnull=True).select_related('item', 'crop', 'recommended_unit')
        
        crop_id_param = request.query_params.get('crop_id') or request.query_params.get('crop')
        item_id_param = request.query_params.get('item_id') or request.query_params.get('item')
        location_id_param = request.query_params.get('location_id') or request.query_params.get('location')
        include_locations = _parse_bool(request.query_params.get('include_locations', 'false'))

        if crop_id_param:
            try:
                qs = qs.filter(crop_id=int(crop_id_param))
            except (ValueError, TypeError):
                return Response({'detail': 'crop_id is invalid'}, status=status.HTTP_400_BAD_REQUEST)
        
        if item_id_param:
            try:
                qs = qs.filter(item_id=int(item_id_param))
            except (ValueError, TypeError):
                pass
        
        if target_farm_ids:
            # Only show materials linked to crops the user has access to in the target farms
            crop_ids = FarmCrop.objects.filter(farm_id__in=target_farm_ids, deleted_at__isnull=True).values_list('crop_id', flat=True)
            qs = qs.filter(crop_id__in=crop_ids)

        # [Agri-Guardian] Performance Optimization:
        # Batch fetch inventory levels to avoid N+1 queries.
        crop_materials = list(qs)
        item_ids = [cm.item_id for cm in crop_materials]
        
        inventory_map = {}
        location_breakdown_map = {} # item_id -> list of {location_id, location_name, qty}

        if item_ids and target_farm_ids:
             # Basic Aggregation
             inv_qs = ItemInventory.objects.filter(
                 item_id__in=item_ids, 
                 farm_id__in=target_farm_ids
             )
             
             if location_id_param:
                 try:
                     inv_qs = inv_qs.filter(location_id=int(location_id_param))
                 except (ValueError, TypeError):
                     pass

             # Overall Sum for the on_hand_qty field
             summary_qs = inv_qs.values('item_id').annotate(total_qty=Sum('qty'))
             inventory_map = {entry['item_id']: entry['total_qty'] for entry in summary_qs}

             # Optional Location Breakdown for "Where is it?" feature
             if include_locations:
                 breakdown_qs = inv_qs.select_related('location').values(
                     'item_id', 'location_id', 'location__name'
                 ).annotate(qty=Sum('qty')).order_by('location__name')
                 
                 for entry in breakdown_qs:
                     iid = entry['item_id']
                     location_breakdown_map.setdefault(iid, []).append({
                         'location_id': entry['location_id'],
                         'location_name': entry['location__name'] or 'المخزن الرئيسي',
                         'qty': entry['qty']
                     })

        data = []
        for cm in crop_materials:
            current_qty = inventory_map.get(cm.item_id, 0)
            data.append({
                 'crop_material_id': cm.id,
                 'crop_id': cm.crop_id,
                 'crop_name': cm.crop.name,
                 'item_id': cm.item_id,
                 'item_name': cm.item.name,
                 'item_group': cm.item.group,
                 'item_material_type': getattr(cm.item, 'material_type', ''),
                 'item_unit_id': cm.item.unit_id,
                 'item_currency': cm.item.currency,
                 'item_unit_price': cm.item.unit_price,
                 'recommended_qty': cm.recommended_qty,
                 'recommended_uom': cm.recommended_uom,
                 'recommended_unit_id': cm.recommended_unit_id,
                 'recommended_unit': UnitSerializer(cm.recommended_unit).data if cm.recommended_unit else None,
                 'on_hand_qty': current_qty, 
                 'on_hand_uom': cm.item.uom, # Fallback to Item defined UOM
                 'on_hand_unit': UnitSerializer(cm.item.unit).data if cm.item.unit else None, 
                 'low_stock': current_qty < (cm.item.reorder_level or 0),
                 'locations': location_breakdown_map.get(cm.item_id, []) if include_locations else None
            })
        
        return Response(data)


class HarvestProductCatalogViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        qs = CropProduct.objects.filter(deleted_at__isnull=True).select_related('crop', 'farm', 'item')
        target_farm_ids = None
        
        farm_id_param = request.query_params.get('farm_id')
        if farm_id_param:
            try:
                if ',' in str(farm_id_param):
                    fids = [int(x) for x in str(farm_id_param).split(',') if x.strip().isdigit()]
                    # Verify access to all
                    valid_fids = []
                    for fid in fids:
                        try:
                            _ensure_user_has_farm_access(request.user, fid)
                            valid_fids.append(fid)
                        except (ValidationError, OperationalError, ValueError) as e:
                            logger.warning(f"Failed farm access check for HarvestProductCatalog: {e}")
                    if valid_fids:
                        target_farm_ids = valid_fids
                        qs = qs.filter(Q(farm_id__in=valid_fids) | Q(farm_id__isnull=True))
                    else:
                        target_farm_ids = []
                        qs = qs.none()
                else:
                    fid = int(farm_id_param)
                    _ensure_user_has_farm_access(request.user, fid)
                    target_farm_ids = [fid]
                    qs = qs.filter(Q(farm_id=fid) | Q(farm_id__isnull=True))
            except (ValueError, TypeError):
                 # Fail safe
                 target_farm_ids = []
                 qs = qs.none()
                 
        elif not request.user.is_superuser:
            farm_ids = user_farm_ids(request.user)
            target_farm_ids = farm_ids
            qs = qs.filter(Q(farm_id__in=farm_ids) | Q(farm_id__isnull=True))
            
        # [Agri-Guardian] Performance Optimization:
        # Batch fetch total harvest quantity to avoid N+1 queries.
        crop_products = list(qs)
        product_ids = [cp.id for cp in crop_products]
        
        harvest_map = {}
        if product_ids:
             # Aggregate harvest quantity for these products across the target farms
             # Note: Different units are not normalized here (Optimization trade-off). 
             # Ideally we should group by product + unit, but UI expects a single total.
             # We assume dominant unit or sum raw values.
             # For Phase 2, we return raw sum and let UI/User interpret.
             from django.db.models import Sum
             lot_qs = HarvestLot.objects.filter(
                 product_id__in=product_ids, 
                 # If target_farm_ids is empty, it means "all allowed" (which logic above handles via qs filtering)
                 # Wait, logic above filtered 'qs' by farm_id. 
                 # So we should filter lots by the same farms to be consistent?
                 # Yes, if valid_fids/farm_ids were used.
             ).values('product_id').annotate(total_qty=Sum('quantity'))
             
             # If specific farm filter was applied to 'qs', we should apply it here too.
             if target_farm_ids: # Using the variable from logical block above? 
                 # Need to check scope. 'target_farm_ids' isn't fully defined in original code snippet 
                 # (it was in MaterialCatalog).
                 # Re-checking HarvestProductCatalog logic:
                 # It used 'qs = qs.filter(... farm_id__in=...)'.
                 # So we can just trust 'product_ids' are from the filtered set.
                 # BUT a product can belong to a farm, while Lots also belong to a farm.
                 # If we are listing Global Products (farm_id=null), we must sum Lots from user's allowed farms.
                 pass
             
             # Refined Logic: Filter Lots by User Access to avoid leaking data for Shared Products
             allowed_farms = user_farm_ids(request.user) if not request.user.is_superuser else None
             if target_farm_ids:
                 lot_qs = lot_qs.filter(farm_id__in=target_farm_ids)
             elif allowed_farms is not None:
                 lot_qs = lot_qs.filter(farm_id__in=allowed_farms)
                
             harvest_map = {entry['product_id']: entry['total_qty'] for entry in lot_qs}

        data = []
        for cp in crop_products:
            unit_data = None
            try:
                if cp.item and cp.item.unit:
                    unit_data = UnitSerializer(cp.item.unit).data
            except (ValidationError, OperationalError, ValueError) as e:
                logger.warning(f"Missing unit or integrity error on CP {cp.id}: {e}")

            current_qty = harvest_map.get(cp.id, 0)
            
            data.append({
                'product_id': cp.id,
                'farm_id': cp.farm_id,
                'farm_name': cp.farm.name if cp.farm else '',
                'crop_id': cp.crop_id,
                'crop_name': cp.crop.name,
                'item_id': getattr(cp, 'item_id', None),
                'item_name': getattr(cp.item, 'name', cp.name) if getattr(cp, 'item', None) else cp.name,
                'name': getattr(cp.item, 'name', cp.name) if getattr(cp, 'item', None) else cp.name,
                'reference_price': cp.reference_price or getattr(cp.item, 'unit_price', 0),
                'item_group': getattr(cp.item, 'group', '') if getattr(cp, 'item', None) else '',
                'default_unit': unit_data,
                'is_primary': cp.is_primary,
                'notes': cp.notes,
                'total_harvest_qty': current_qty, 
            })
        return Response(data)


# --- Tree Inventory ViewSets MOVED to smart_agri.inventory.api.viewsets ---

from smart_agri.core.models.inventory import BiologicalAssetCohort, BiologicalAssetTransaction, TreeCensusVarianceAlert
from smart_agri.core.api.serializers.inventory import BiologicalAssetCohortSerializer, BiologicalAssetTransactionSerializer, TreeCensusVarianceAlertSerializer
from smart_agri.core.services.tree_census_service import TreeCensusService

class BiologicalAssetCohortViewSet(AuditedModelViewSet):
    """
    [AGRI-GUARDIAN] Axis 11 Compliance: Biological Asset Hierarchy
    REST API for managing perennial tree batches (Asset Cohorts).
    """
    queryset = BiologicalAssetCohort.objects.all().select_related('farm', 'location', 'crop', 'variety', 'parent_cohort')
    serializer_class = BiologicalAssetCohortSerializer
    model_name = "BiologicalAssetCohort"
    
    def get_queryset(self):
        qs = super().get_queryset()
        qs = _limit_queryset_to_user_farms(qs, self.request.user, 'farm_id__in')
        
        farm_id = self.request.query_params.get('farm') or self.request.query_params.get('farm_id')
        location_id = self.request.query_params.get('location') or self.request.query_params.get('location_id')
        crop_id = self.request.query_params.get('crop') or self.request.query_params.get('crop_id')
        variety_id = self.request.query_params.get('variety') or self.request.query_params.get('variety_id')
        status_filter = self.request.query_params.get('status')
        parent_cohort_id = self.request.query_params.get('parent_cohort')
        
        if farm_id: qs = qs.filter(farm_id=farm_id)
        if location_id: qs = qs.filter(location_id=location_id)
        if crop_id: qs = qs.filter(crop_id=crop_id)
        if variety_id: qs = qs.filter(variety_id=variety_id)
        if status_filter: qs = qs.filter(status__iexact=status_filter)
        if parent_cohort_id: qs = qs.filter(parent_cohort_id=parent_cohort_id)
        
        return qs.order_by('planted_date')

    @action(detail=False, methods=['get'], url_path='aggregate_by_location')
    def aggregate_by_location(self, request):
        """
        Returns aggregated quantities of all cohorts for a specific location+crop+variety.
        Used by DailyLog.jsx to display summarized info to the worker.
        """
        farm_id = request.query_params.get('farm') or request.query_params.get('farm_id')
        location_id = request.query_params.get('location') or request.query_params.get('location_id')
        crop_id = request.query_params.get('crop') or request.query_params.get('crop_id')
        variety_id = request.query_params.get('variety') or request.query_params.get('variety_id')
        
        if not all([farm_id, location_id, crop_id]):
            return Response({'detail': 'farm, location, and crop are required.'}, status=400)
            
        _ensure_user_has_farm_access(request.user, farm_id)
        
        qs = BiologicalAssetCohort.objects.filter(
            farm_id=farm_id,
            location_id=location_id,
            crop_id=crop_id,
            deleted_at__isnull=True
        )
        
        if variety_id:
            qs = qs.filter(variety_id=variety_id)
            
        aggregates = qs.values('status').annotate(total=Sum('quantity'))
        
        result = {
            'JUVENILE': 0,
            'PRODUCTIVE': 0,
            'SICK': 0,
            'RENEWING': 0,
            'EXCLUDED': 0,
            'TOTAL_ALIVE': 0
        }
        
        for item in aggregates:
            status_val = item['status']
            total = item['total'] or 0
            result[status_val] = total
            if status_val in ['JUVENILE', 'PRODUCTIVE', 'SICK', 'RENEWING']:
                result['TOTAL_ALIVE'] += total
                
        return Response(result)

    def perform_destroy(self, instance):
        """
        [AGRI-GUARDIAN] Best Practice: Append-only forensic trail on cohort deletion.
        Before soft-deleting, record a BiologicalAssetTransaction with EXCLUDED status
        as an immutable audit entry. This lets us trace who deleted what and when.
        """
        from django.db import transaction as db_transaction
        with db_transaction.atomic():
            try:
                BiologicalAssetTransaction.objects.create(
                    cohort=instance,
                    farm=instance.farm,
                    from_status=instance.status,
                    to_status=BiologicalAssetCohort.STATUS_EXCLUDED,
                    quantity=instance.quantity,
                    notes=(
                        f"[Admin Delete] حذف الدفعة يدوياً بواسطة "
                        f"{getattr(self.request.user, 'username', 'unknown')}. "
                        f"السبب: {self.request.data.get('audit_reason', 'حذف إداري')}"
                    ),
                    reference_id=f"admin-delete-{instance.pk}",
                )
            except (DjangoValidationError, DatabaseError, IntegrityError, ValueError, TypeError, AttributeError) as exc:
                logger.warning(
                    "AUDIT_WARN: Failed to create transaction record for cohort delete pk=%s: %s",
                    instance.pk, exc
                )
            # Soft delete via SoftDeleteModel.delete()
            super().perform_destroy(instance)

    @action(detail=True, methods=['post'], url_path='transition')
    def transition(self, request, pk=None):
        """
        @idempotent
        [AGRI-GUARDIAN] Axis 11 Compliance: Biological Asset Transition
        Moves part or all of a cohort to a new state.
        If target_status is EXCLUDED (Death/Loss), it generates a VarianceAlert for management approval instead.
        """
        key, error_response = self._enforce_action_idempotency(request)
        if error_response:
            return error_response

        cohort = self.get_object()
        target_status = request.data.get('target_status')
        try:
            qty_to_move = int(request.data.get('quantity', 0))
        except (ValueError, TypeError):
            return Response({'detail': 'كمية غير صالحة.'}, status=status.HTTP_400_BAD_REQUEST)
        
        notes = request.data.get('notes', '')

        valid_statuses = dict(BiologicalAssetCohort.STATUS_CHOICES)
        if target_status not in valid_statuses:
            return Response({'detail': f'حالة غير صالحة. المدعوم: {list(valid_statuses.keys())}'}, status=status.HTTP_400_BAD_REQUEST)

        if cohort.status == target_status:
            return Response({'detail': 'الدفعة في نفس الحالة المطلوبة.'}, status=status.HTTP_400_BAD_REQUEST)

        if qty_to_move <= 0 or qty_to_move > cohort.quantity:
            return Response({'detail': f'الكمية يجب أن تكون بين 1 و {cohort.quantity}.'}, status=status.HTTP_400_BAD_REQUEST)

        if target_status == BiologicalAssetCohort.STATUS_EXCLUDED:
            # Generate Variance Alert instead of direct deletion
            with transaction.atomic():
                alert = TreeCensusVarianceAlert.objects.create(
                    log=None,  # Nullable log 
                    farm=cohort.farm,
                    location=cohort.location,
                    crop=cohort.crop,
                    cohort=cohort,
                    missing_quantity=qty_to_move,
                    reason=notes or 'نقص مدخل يدوياً من الشاشة',
                    status=TreeCensusVarianceAlert.STATUS_PENDING
                )
            response = Response({
                'detail': f'تم رفع بلاغ إعدام/نقص برقم #{alert.pk} لطلب اعتماد الإدارة.',
                'alert_id': alert.pk
            }, status=status.HTTP_202_ACCEPTED)
            self._commit_action_idempotency(request, key, object_id=str(cohort.id), response=response)
            return response

        # Regular transition (JUVENILE <-> PRODUCTIVE <-> SICK, etc.)
        with transaction.atomic():
            # Refresh from DB with lock
            cohort = BiologicalAssetCohort.objects.select_for_update().get(pk=cohort.pk)
            if qty_to_move > cohort.quantity:
                return Response({'detail': 'تغيرت كمية الدفعة أثناء التنفيذ.'}, status=status.HTTP_400_BAD_REQUEST)

            old_status = cohort.status
            new_cohort = None

            if qty_to_move == cohort.quantity:
                # Full transition
                cohort.status = target_status
                cohort.save(update_fields=['status', 'updated_at'])
                BiologicalAssetTransaction.objects.create(
                    cohort=cohort,
                    farm=cohort.farm,
                    from_status=old_status,
                    to_status=target_status,
                    quantity=qty_to_move,
                    notes=f"[Full Transition] {notes}".strip(),
                    reference_id=f"transition-{cohort.pk}"
                )
            else:
                # Partial transition (Split)
                cohort.quantity -= qty_to_move
                cohort.save(update_fields=['quantity', 'updated_at'])
                
                # Create sibling cohort
                new_cohort = BiologicalAssetCohort.objects.create(
                    farm=cohort.farm,
                    location=cohort.location,
                    crop=cohort.crop,
                    variety=cohort.variety,
                    parent_cohort=cohort.parent_cohort,
                    batch_name=f"{cohort.batch_name} (منشقة - {valid_statuses[target_status]})",
                    status=target_status,
                    quantity=qty_to_move,
                    planted_date=cohort.planted_date,
                    capitalized_cost=0, # If splitting costs, we would prorate here. Leaving as 0.
                )
                
                BiologicalAssetTransaction.objects.create(
                    cohort=cohort,
                    farm=cohort.farm,
                    from_status=old_status,
                    to_status=target_status,  # Showing it left this cohort to this status
                    quantity=qty_to_move,
                    notes=f"[Split Out] انفصلت لتكوين الدفعة الجديدة #{new_cohort.pk}. {notes}".strip(),
                    reference_id=f"split-out-{cohort.pk}"
                )
                BiologicalAssetTransaction.objects.create(
                    cohort=new_cohort,
                    farm=new_cohort.farm,
                    from_status=old_status,
                    to_status=target_status,
                    quantity=qty_to_move,
                    notes=f"[Split In] أنشئت من الدفعة #{cohort.pk}. {notes}".strip(),
                    reference_id=f"split-in-{new_cohort.pk}"
                )
            
            response_serializer = BiologicalAssetCohortSerializer(new_cohort or cohort)
            response = Response(response_serializer.data, status=status.HTTP_200_OK)
            self._commit_action_idempotency(request, key, object_id=str(cohort.id), response=response)
            return response

class MassCasualtyWriteoffViewSet(viewsets.ViewSet):
    """
    [AGENTS.md §Axis-18] Mass Casualty Authoritative API.
    Handles extraordinary biological asset losses with C-Level authorization.
    """
    permission_classes = [permissions.IsAuthenticated, StrictErpOnlyPermission]
    
    @action(detail=False, methods=['post'], url_path='execute')
    def execute(self, request):
        if MassCasualtyWriteoffService is None:
            return Response({"error": "MassCasualtyWriteoffService not found."}, status=500)
            
        serializer = MassCasualtyWriteoffRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        data = serializer.validated_data
        
        # [FORENSIC CHECK]: Verify manager exists and has authority
        # (Authority checks are partially inside the service, but we guard here too)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            manager = User.objects.get(pk=data['approved_by_manager_id'])
            auditor = User.objects.get(pk=data['approved_by_auditor_id']) if data.get('approved_by_auditor_id') else None
        except User.DoesNotExist:
            return Response({"error": "Manager or Auditor user not found."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = MassCasualtyWriteoffService.execute_mass_writeoff(
                farm_id=data['farm_id'],
                cohort_entries=data['cohort_entries'],
                cause=data['cause'],
                reason=data['reason'],
                user=request.user,
                approved_by_manager=manager,
                approved_by_auditor=auditor,
                idempotency_key=data['idempotency_key']
            )
            return Response(result, status=status.HTTP_200_OK)
        except DjangoValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except (DjangoValidationError, PermissionDenied, IntegrityError, DatabaseError, RuntimeError, ValueError) as e:
            logger.exception("Mass Casualty execution failed")
            return Response({"error": "Internal server error during write-off execution."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class BiologicalAssetTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    [AGRI-GUARDIAN] Axis 11 Compliance: Capital Event Ledger
    Read-only view for tracking historical state transitions.
    """
    queryset = BiologicalAssetTransaction.objects.all().select_related('cohort', 'farm')
    serializer_class = BiologicalAssetTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = _limit_queryset_to_user_farms(qs, self.request.user, 'farm_id__in')
        cohort_id = self.request.query_params.get('cohort')
        
        if cohort_id:
            qs = qs.filter(cohort_id=cohort_id)
        return qs

class TreeCensusVarianceAlertViewSet(AuditedModelViewSet):
    """
    [AGRI-GUARDIAN] Axis 11 Compliance: Loss Prevention Ledger
    Exposes tree census variance alerts for management review.
    """
    queryset = TreeCensusVarianceAlert.objects.all().select_related('farm', 'location', 'crop', 'log', 'resolved_by')
    serializer_class = TreeCensusVarianceAlertSerializer
    model_name = "TreeCensusVarianceAlert"

    def get_queryset(self):
        qs = super().get_queryset()
        qs = _limit_queryset_to_user_farms(qs, self.request.user, 'farm_id__in')
        
        farm_id = self.request.query_params.get('farm') or self.request.query_params.get('farm_id')
        location_id = self.request.query_params.get('location') or self.request.query_params.get('location_id')
        status_filter = self.request.query_params.get('status')
        log_id = self.request.query_params.get('log') or self.request.query_params.get('log_id')
        
        if farm_id: qs = qs.filter(farm_id=farm_id)
        if location_id: qs = qs.filter(location_id=location_id)
        if status_filter: qs = qs.filter(status__iexact=status_filter)
        if log_id: qs = qs.filter(log_id=log_id)
        
        return qs.order_by('-created_at')


    @action(detail=True, methods=['post'], url_path='resolve')
    def resolve(self, request, pk=None):
        """
        @idempotent
        [AGRI-GUARDIAN] Axis 11 Compliance: Full Loss Reconciliation Workflow.
        """
        key, error_response = self._enforce_action_idempotency(request)
        if error_response:
            return error_response
        alert = self.get_object()

        if alert.status == TreeCensusVarianceAlert.STATUS_RESOLVED:
            return Response({'detail': 'التنبيه تم اعتماده مسبقاً.'}, status=status.HTTP_400_BAD_REQUEST)

        cohort_id = request.data.get('cohort_id')
        create_ratoon = request.data.get('create_ratoon', False)
        notes = request.data.get('notes', '')

        if not cohort_id:
            return Response({'detail': 'يجب تحديد دفعة الغرس (cohort_id) المستهدفة بالخصم.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = TreeCensusService.resolve_variance_alert(
                alert=alert,
                cohort_id=cohort_id,
                actor=request.user,
                notes=notes,
                create_ratoon=_parse_bool(create_ratoon),
            )
            cohort = result['cohort']
            ratoon_cohort = result['ratoon_cohort']

            response_data = TreeCensusVarianceAlertSerializer(result['alert']).data
            response_data['deducted_from_cohort'] = str(cohort)
            response_data['cohort_remaining_quantity'] = cohort.quantity
            if ratoon_cohort:
                response_data['ratoon_cohort_id'] = ratoon_cohort.pk
                response_data['ratoon_cohort_name'] = ratoon_cohort.batch_name

            response = Response(response_data)
            self._commit_action_idempotency(request, key, object_id=str(alert.id), response=response)
            return response

        except DRFValidationError as exc:
            return Response(getattr(exc, 'detail', {'detail': str(exc)}), status=status.HTTP_400_BAD_REQUEST)
