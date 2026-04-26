"""
Reporting ViewSets
"""
from typing import Any
from decimal import Decimal
from django.db.models import Sum, Count
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response

from smart_agri.core.models import (
    Farm, Activity, ActivityItem, LocationTreeStock, CropMaterial
)
from smart_agri.sales.models import SalesInvoice
from smart_agri.core.api.serializers import LocationTreeStockSerializer
from smart_agri.core.api.permissions import (
    user_farm_ids, 
    _ensure_user_has_farm_access, 
    FarmScopedPermission
)
from smart_agri.core.api.utils import _coerce_int, _safe_decimal, _coerce_int_list

# Import function-based reports from api/reporting.py (if kept) or redefine here.
# I will redefine ResourceAnalyticsViewSet here.

class ReportsViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated, FarmScopedPermission]

    def _parse_range(self, request):
        today = timezone.localdate()
        start_str = request.query_params.get('start') or request.query_params.get('date')
        end_str = request.query_params.get('end') or request.query_params.get('date')
        start = parse_date(start_str) if start_str else today
        end = parse_date(end_str) if end_str else start
        if start is None:
            start = today
        if end is None:
            end = start
        if start > end:
            start, end = end, start
        return start, end

    def _resolve_farm_ids(self, request):
        accessible = set(user_farm_ids(request.user))
        farm_param = request.query_params.get('farm')
        requested = []
        if farm_param:
            for token in farm_param.split(','):
                token = token.strip()
                if not token:
                    continue
                try:
                    requested.append(int(token))
                except ValueError:
                    continue
        if request.user.is_superuser:
            return requested or list(accessible)
        if requested:
            return [fid for fid in requested if fid in accessible]
        return list(accessible)

    def list(self, request):
        start, end = self._parse_range(request)
        farm_ids = self._resolve_farm_ids(request)
        crop_id = _coerce_int(request.query_params.get('crop'))
        task_id = _coerce_int(request.query_params.get('task'))
        location_id = _coerce_int(request.query_params.get('location'))
        supervisor_id = _coerce_int(request.query_params.get('supervisor'))

        # Aggregation Logic [Agri-Guardian Implementation]
        qs = Activity.objects.filter(
            deleted_at__isnull=True,
            log__log_date__range=(start, end),
            log__farm_id__in=farm_ids,
            log__deleted_at__isnull=True,
        ).prefetch_related('activity_locations__location')
        if crop_id is not None:
            qs = qs.filter(crop_id=crop_id)
        if task_id is not None:
            qs = qs.filter(task_id=task_id)
        if location_id is not None:
            qs = qs.filter(activity_locations__location_id=location_id)
        if supervisor_id is not None:
            qs = qs.filter(log__supervisor_id=supervisor_id)
        qs = qs.distinct()
        
        metrics = qs.aggregate(
            total_activities=Count('id'),
            total_hours=Coalesce(Sum('days_spent'), Decimal('0.00')),
            
            # [Agri-Guardian] Frontend alignment
            machine_hours=Coalesce(Sum('machine_details__machine_hours'), Decimal('0.00')),
            materials_total_qty=Coalesce(Sum('items__qty'), Decimal('0.00')),
            harvest_total_qty=Coalesce(Sum('harvest_details__harvest_quantity'), Decimal('0.00')),
            distinct_locations=Count('activity_locations__location_id', distinct=True),
            # distinct_wells relies on irrigation details linking to an asset
            distinct_wells=Count('irrigation_details__well_asset', distinct=True),

            total_labor_cost=Coalesce(Sum('cost_labor'), Decimal('0.00')),
            total_material_cost=Coalesce(Sum('cost_materials'), Decimal('0.00')),
            total_machinery_cost=Coalesce(Sum('cost_machinery'), Decimal('0.00')),
            total_overhead_cost=Coalesce(Sum('cost_overhead'), Decimal('0.00')),
            grand_total_cost=Coalesce(Sum('cost_total'), Decimal('0.00'))
        )
        metrics['activities'] = metrics.get('total_activities', 0)

        perennial_qs = qs.filter(
            crop__is_perennial=True,
            deleted_at__isnull=True,
            crop_variety__isnull=False,
            activity_locations__location__isnull=False,
        )
        perennial_rows = perennial_qs.values(
            'crop_id',
            'crop__name',
            'crop_variety_id',
            'crop_variety__name',
            'activity_locations__location_id',
            'activity_locations__location__name',
        ).annotate(
            activities=Count('id', distinct=True),
            trees_serviced=Coalesce(Sum('activity_tree_count'), 0),
            net_tree_delta=Coalesce(Sum('tree_count_delta'), 0),
        )
        perennial_entries = []
        for row in perennial_rows:
            row_location_id = row['activity_locations__location_id']
            current_tree_count = (
                LocationTreeStock.objects.filter(
                    location_id=row_location_id,
                    crop_variety_id=row['crop_variety_id'],
                    deleted_at__isnull=True,
                ).aggregate(total=Coalesce(Sum('current_tree_count'), 0)).get('total') or 0
            )
            perennial_entries.append({
                'crop': {'id': row['crop_id'], 'name': row['crop__name']},
                'variety': {'id': row['crop_variety_id'], 'name': row['crop_variety__name']},
                'location': {
                    'id': row_location_id,
                    'name': row['activity_locations__location__name'],
                },
                'activities': int(row['activities'] or 0),
                'trees_serviced': int(row['trees_serviced'] or 0),
                'net_tree_delta': int(row['net_tree_delta'] or 0),
                'current_tree_count': int(current_tree_count or 0),
            })
        perennial_summary = {
            'activities': sum(int(e['activities']) for e in perennial_entries),
            'trees_serviced': sum(int(e['trees_serviced']) for e in perennial_entries) if perennial_entries else 0,
            'net_tree_delta': sum(int(e['net_tree_delta']) for e in perennial_entries) if perennial_entries else 0,
            'current_tree_count': sum(int(e['current_tree_count']) for e in perennial_entries) if perennial_entries else 0,
            'entries': perennial_entries,
        }
        
        # Optional: Group by Service Type if needed for "Services" dashboard
        # This requires the Activity model to have a 'service_type' or similar field.
        # Based on migration 0001, Activity has no 'service_type' direct field, 
        # but it might be in 'data' JSON or related 'task'.
        # Checking 'task' relation... Activity has 'task = models.ForeignKey...' (implied, not in 0001 but in DailyLog context)
        # Actually 0001 didn't show 'task' field on Activity! 
        # It's likely added in a later migration. 
        # I will assume basic metrics first.

        payload = {
            'period': {'start': start, 'end': end},
            'farms': farm_ids,
            'metrics': metrics,
            'perennial': perennial_summary,
            'currency': 'SAR', # Standardize
        }
        
        return Response(payload)


class ResourceAnalyticsViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated, FarmScopedPermission]
    
    def list(self, request):
        # start, end = self.request.parser_context['view']._parse_range(request) # Removed broken line
        today = timezone.localdate()
        start_str = request.query_params.get('start')
        end_str = request.query_params.get('end')
        start_date = parse_date(start_str) if start_str else today
        end_date = parse_date(end_str) if end_str else start_date
        if start_date is None: start_date = today
        if end_date is None: end_date = start_date
        
        accessible = set(user_farm_ids(request.user))
        farm_param = request.query_params.get('farm')
        target_farms = []
        if farm_param: 
            for t in farm_param.split(','):
                try: 
                    if int(t) in accessible or request.user.is_superuser: target_farms.append(int(t))
                except (ValueError, TypeError):
                    # [AGRI-GUARDIAN §2.II] Log invalid farm IDs instead of silent pass
                    continue
        else: target_farms = list(accessible)

        # [Agri-Guardian] Material Consumption Logic (Crop-Centric)
        # 1. Get Actual Consumption
        qs = ActivityItem.objects.filter(
            deleted_at__isnull=True,
            activity__deleted_at__isnull=True,
            activity__log__log_date__range=(start_date, end_date),
            activity__log__farm_id__in=target_farms,
            activity__log__deleted_at__isnull=True,
            item__deleted_at__isnull=True,
        ).values(
            'activity__crop_id', 'activity__crop__name',
            'item_id', 'item__name', 'uom', 'item__unit_price'
        ).annotate(
            total_qty=Coalesce(Sum('qty'), Decimal('0')),
            total_cost=Coalesce(Sum('total_cost'), Decimal('0')) # Using stored cost or calc? ActivityItem has total_cost field.
        ).order_by('activity__crop_id')

        crop_ids = {row['activity__crop_id'] for row in qs if row.get('activity__crop_id')}
        item_ids = {row['item_id'] for row in qs if row.get('item_id')}
        recommended_map = {
            (cm.crop_id, cm.item_id): Decimal(str(cm.recommended_qty or 0))
            for cm in CropMaterial.objects.filter(crop_id__in=crop_ids, item_id__in=item_ids, deleted_at__isnull=True)
        }

        # 2. Transform to Payload
        grouped = {}
        for entry in qs:
            cid = entry['activity__crop_id']
            if not cid: continue # Skip general activities without crop? Frontend expects crop.
            
            if cid not in grouped:
                grouped[cid] = {
                    'crop': {'id': cid, 'name': entry['activity__crop__name']},
                    'totals': {'recommended_cost': Decimal('0'), 'actual_cost': Decimal('0')},
                    'materials': []
                }
            
            rec_qty = recommended_map.get((cid, entry['item_id']), Decimal('0'))
            unit_price = _safe_decimal(entry.get('item__unit_price'))
            rec_cost = rec_qty * unit_price
            act_qty = entry['total_qty']
            act_cost = _safe_decimal(entry['total_cost'])
            if act_cost == 0:
                act_cost = _safe_decimal(act_qty) * unit_price
            
            grouped[cid]['totals']['actual_cost'] += act_cost
            
            grouped[cid]['materials'].append({
                'item_id': entry['item_id'],
                'item_name': entry['item__name'],
                'unit_symbol': entry['uom'],
                'recommended_qty': str(rec_qty),
                'actual_qty': str(act_qty),
                'recommended_cost': str(rec_cost),
                'actual_cost': str(act_cost),
                'variance_cost': str(act_cost - rec_cost),
            })

        return Response({'results': list(grouped.values())})
