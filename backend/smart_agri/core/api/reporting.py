"""
Reporting API
ÙˆØ§Ø¬Ù‡Ø© Ø¨Ø±Ù…Ø¬Ø© ØªØ·Ø¨ÙŠÙ‚Ø§Øª Ø§Ù„ØªÙ‚Ø§Ø±ÙŠØ±
"""
import logging
import math
import json
from pathlib import Path
from collections import defaultdict
from decimal import Decimal

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError, PermissionDenied
from rest_framework.test import force_authenticate
from django.utils import timezone
from django.db import DatabaseError, OperationalError
from django.db.models import Sum, Count, Q, F
from django.db.models.functions import Coalesce
from django.db.models import Value, DecimalField, IntegerField
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder

# Ø§Ù„Ø¢Ù† ÙŠÙ…ÙƒÙ†Ù†Ø§ Ø§Ø³ØªÙŠØ±Ø§Ø¯ ActivityItem Ø¨Ø£Ù…Ø§Ù†
from smart_agri.core.models import (
    Farm, Activity, ActivityItem, LocationWell, DailyLog, CropPlan, 
    LocationTreeStock, TreeStockEvent
)
from smart_agri.core.api.serializers.activity import ActivitySerializer
from smart_agri.core.api.serializers.tree import LocationTreeStockSerializer, TreeStockEventSerializer
from smart_agri.core.api.permissions import _limit_queryset_to_user_farms
from smart_agri.core.api.utils import (
    _coerce_int,
    _parse_bool,
    _apply_tree_filters,
    _safe_decimal,
)
from smart_agri.core.models.report import AsyncReportRequest
from smart_agri.core.services.reporting_orchestration_service import ReportingOrchestrationService
from smart_agri.core.api.reporting_support import (
    build_activity_queryset,
    build_recent_logs_payload,
    parse_advanced_report_context,
)

logger = logging.getLogger(__name__)


def _build_risk_zone_payload(*, farm_id, crop_id, season_id):
    from smart_agri.core.models.activity import ActivityItem
    from smart_agri.core.models.crop import CropRecipeMaterial

    if not farm_id or not crop_id:
        return []

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
    return results


def _generate_advanced_report_inline(job: AsyncReportRequest):
    """Fallback execution when Celery is unavailable in runtime."""
    from rest_framework.test import APIRequestFactory
    from django.contrib.auth.models import AnonymousUser

    job.mark_running()
    params = job.params or {}
    factory = APIRequestFactory()
    internal_request = factory.get("/api/v1/advanced-report/", data=params)
    force_authenticate(internal_request, user=job.created_by or AnonymousUser())

    try:
        response = advanced_report(internal_request)
    except (DatabaseError, RuntimeError, ValueError, TypeError, AttributeError, KeyError) as exc:
        logger.exception("advanced_report crashed during inline generation for job %s", job.id)
        job.mark_failed(f"Internal error: {exc}")
        raise ValueError(f"Advanced report generation crashed: {exc}")

    if response.status_code != 200:
        error_detail = ""
        try:
            error_detail = str(response.data) if hasattr(response, 'data') else str(response.content)
        except (TypeError, ValueError, AttributeError):
            error_detail = f"status={response.status_code}"
        logger.error(
            "advanced_report returned status %s for job %s: %s",
            response.status_code, job.id, error_detail[:500]
        )
        job.mark_failed(f"Report generation failed (status {response.status_code}): {error_detail[:200]}")
        raise ValueError(f"Advanced report generation failed with status {response.status_code}")

    media_root = Path(settings.MEDIA_ROOT)
    reports_dir = media_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    filename = f"advanced-report-{job.id}.json"
    file_path = reports_dir / filename
    with file_path.open("w", encoding="utf-8") as fh:
        json.dump(response.data, fh, ensure_ascii=False, indent=2, cls=DjangoJSONEncoder)

    job.mark_completed(f"/media/reports/{filename}")

def _generate_profitability_report_inline(job: AsyncReportRequest):
    """Fallback execution for PDF profitability report when Celery is unavailable."""
    from smart_agri.core.services.reporting_service import ArabicReportService
    job.mark_running()
    try:
        service = ArabicReportService()
        params = job.params or {}
        pdf_bytes = service.generate_profitability_pdf(params)
        
        media_root = Path(settings.MEDIA_ROOT)
        reports_dir = media_root / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        filename = f"profitability_report_{job.id}.pdf"
        file_path = reports_dir / filename
        
        with file_path.open("wb") as fh:
            fh.write(pdf_bytes)
            
        pdf_url = f"/media/reports/{filename}"
        job.mark_completed(pdf_url)
    except (ValidationError, OperationalError, ValueError) as exc:
        job.mark_failed(f"Internal error: {exc}")
        raise ValueError(f"Advanced profitability report generation crashed: {exc}")


def _generate_commercial_report_inline(job: AsyncReportRequest):
    """Fallback execution for commercial PDF report when Celery is unavailable."""
    from smart_agri.core.services.reporting_service import ArabicReportService

    job.mark_running()
    try:
        service = ArabicReportService()
        params = job.params or {}
        pdf_bytes = service.generate_commercial_pdf(params)

        media_root = Path(settings.MEDIA_ROOT)
        reports_dir = media_root / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        filename = f"commercial_report_{job.id}.pdf"
        file_path = reports_dir / filename

        with file_path.open("wb") as fh:
            fh.write(pdf_bytes)

        pdf_url = f"/media/reports/{filename}"
        job.mark_completed(pdf_url)
    except (ValidationError, OperationalError, ValueError) as exc:
        job.mark_failed(f"Internal error: {exc}")
        raise ValueError(f"Advanced commercial report generation crashed: {exc}")


def _resolve_inline_generator(job: AsyncReportRequest):
    if job.report_type == AsyncReportRequest.REPORT_PROFITABILITY:
        return _generate_profitability_report_inline
    if job.report_type == AsyncReportRequest.REPORT_COMMERCIAL_PDF:
        return _generate_commercial_report_inline
    return _generate_advanced_report_inline

# [Agri-Guardian]: Fix mixed types (Decimal vs Float). Must use DecimalField.
@api_view(['GET'])
def advanced_report(request):
    """
    Ù†Ù‚Ø·Ø© Ø§Ù„Ù†Ù‡Ø§ÙŠØ© Ø§Ù„Ù…Ø´ØºÙ„Ø© Ù„Ù„ÙˆØ­Ø© Ù…Ø¹Ù„ÙˆÙ…Ø§Øª Ø§Ù„ØªÙ‚Ø§Ø±ÙŠØ± Ø§Ù„Ù…ØªÙ‚Ø¯Ù…Ø©.
    ØªØ¹ÙŠØ¯ Ù…Ù‚Ø§ÙŠÙŠØ³ Ø§Ù„Ù…Ù„Ø®ØµØŒ ÙˆØ¨ÙŠØ§Ù†Ø§Øª Ø§Ù„Ø±Ø³Ù… Ø§Ù„Ø¨ÙŠØ§Ù†ÙŠØŒ ÙˆØ§Ù„Ø£Ù†Ø´Ø·Ø© Ø§Ù„ØªÙØµÙŠÙ„ÙŠØ© ÙÙŠ Ø­Ù…ÙˆÙ„Ø© ÙˆØ§Ø­Ø¯Ø©.
    """
    try:
        context = parse_advanced_report_context(request)
        start = context.start
        end = context.end
        farm_ids = context.farm_ids
        include_tree_inventory = context.include_tree_inventory
        tree_filters = context.tree_filters
        include_details = context.include_details
        section_scope = context.section_scope

        activity_qs = build_activity_queryset(context=context)
    
        metrics = activity_qs.aggregate(
            total_hours=Coalesce(Sum('days_spent'), Value(0, output_field=DecimalField())),
            machine_hours=Coalesce(Sum('machine_details__machine_hours'), Value(0, output_field=DecimalField())),
            harvest_total_qty=Coalesce(Sum('harvest_details__harvest_quantity'), Value(0, output_field=DecimalField())),
            well_reading_total=Coalesce(Sum('irrigation_details__well_reading'), Value(0, output_field=DecimalField())),
            planting_total_area=Coalesce(Sum('planting_details__planted_area'), Value(0, output_field=DecimalField())),
        )
        
        # Ø§Ø³ØªØ¹Ø§Ø¯Ø© Ø­Ø³Ø§Ø¨ Ø§Ù„Ù…ÙˆØ§Ø¯
        materials_aggregate = ActivityItem.objects.filter(activity__in=activity_qs).aggregate(total_qty=Coalesce(Sum('qty'), Value(0, output_field=DecimalField())))
        metrics['materials_total_qty'] = materials_aggregate.get('total_qty') or 0
        
        tree_activity_qs = activity_qs.filter(
            Q(task__is_perennial_procedure=True) | Q(task__requires_tree_count=True)
        )
        tree_activity_stats = tree_activity_qs.aggregate(
            activities=Count('id'),
            trees_serviced=Coalesce(Sum('activity_tree_count'), Value(0, output_field=IntegerField())),
            net_tree_delta=Coalesce(Sum('tree_count_delta'), Value(0, output_field=IntegerField())),
            loss_tree_delta=Coalesce(Sum('tree_count_delta', filter=Q(tree_count_delta__lt=0)), Value(0, output_field=IntegerField())),
            gain_tree_delta=Coalesce(Sum('tree_count_delta', filter=Q(tree_count_delta__gt=0)), Value(0, output_field=IntegerField())),
        )
        well_asset_ids = set(
            activity_qs.filter(well_asset__isnull=False).values_list('well_asset_id', flat=True)
        )
        legacy_well_ids = set(
            activity_qs.filter(well_asset__isnull=True, asset__category='Well').values_list('asset_id', flat=True)
        )
        distinct_wells = len({wid for wid in well_asset_ids if wid} | {wid for wid in legacy_well_ids if wid})
    
        # Ø§Ø³ØªØ¹Ø§Ø¯Ø© Ù‚Ø§Ø¦Ù…Ø© Ø§Ù„Ù…ÙˆØ§Ø¯
        material_rows = list(
            ActivityItem.objects.filter(activity__in=activity_qs)
            .values('item_id', 'item__name', 'uom', 'item__uom')
            .annotate(total_qty=Sum('qty'), usage_count=Count('id'))
            .order_by('-total_qty')[:10]
        )
        materials_payload = [
            {
                'id': row['item_id'],
                'name': row['item__name'],
                'uom': row['uom'] or row['item__uom'] or '',
                'total_qty': _safe_decimal(row.get('total_qty')),
                'usage_count': row['usage_count'],
            }
            for row in material_rows
            if row['item_id']
        ]
    
        task_rows = list(
            activity_qs
            .filter(task__isnull=False)
            .values('task', 'task__name', 'task__stage', 'crop__id', 'crop__name')
            .annotate(activities=Count('id'), total_hours=Sum('days_spent'))
            .order_by('-activities', '-total_hours')[:5]
        )
        tasks_payload = [
            {
                'task_id': row['task'],
                'task_name': row['task__name'],
                'stage': row['task__stage'],
                'crop_id': row['crop__id'],
                'crop_name': row['crop__name'],
                'activities': row['activities'],
                'total_hours': _safe_decimal(row.get('total_hours')),
            }
            for row in task_rows
        ]
    
        recent_logs_payload = build_recent_logs_payload(activity_qs=activity_qs)
    
        location_rows = list(
            activity_qs
            .filter(activity_locations__location__isnull=False)
            .values(
                location_id=F('activity_locations__location_id'),
                location__name=F('activity_locations__location__name'),
                location__farm_id=F('activity_locations__location__farm_id'),
                location__farm__name=F('activity_locations__location__farm__name'),
            )
            .annotate(
                total_hours=Sum('days_spent'),
                activities=Count('id'),
                machine_hours=Sum('machine_details__machine_hours'),
                materials_total_qty=Sum('items__qty'), # Ø§Ø³ØªØ¹Ø§Ø¯Ø© Ø§Ù„ØªØ¬Ù…ÙŠØ¹ Ù‡Ù†Ø§
                harvest_total_qty=Sum('harvest_details__harvest_quantity'),
                well_reading_total=Sum('irrigation_details__well_reading'),
                planting_total_area=Sum('planting_details__planted_area'),
            )
            .order_by('-total_hours')[:10]
        )
        location_ids = [row['location_id'] for row in location_rows if row['location_id']]
        location_wells_map = defaultdict(set)
        if location_ids:
            for link in LocationWell.objects.filter(location_id__in=location_ids).select_related('asset'):
                if link.asset and link.asset.name:
                    location_wells_map[link.location_id].add(link.asset.name)
    
        activity_well_map = defaultdict(set)
        for loc_id, well_name in activity_qs.filter(
            well_asset__isnull=False, activity_locations__location__isnull=False
        ).values_list('activity_locations__location_id', 'well_asset__name'):
            if loc_id and well_name:
                activity_well_map[loc_id].add(well_name)
    
        for loc_id, well_name in activity_qs.filter(
            well_asset__isnull=True, asset__category='Well', activity_locations__location__isnull=False
        ).values_list('activity_locations__location_id', 'asset__name'):
            if loc_id and well_name:
                activity_well_map[loc_id].add(well_name)
    
        locations_payload = [
            {
                'id': row['location_id'],
                'name': row['location__name'],
                'farm_id': row['location__farm_id'],
                'farm_name': row['location__farm__name'],
                'total_hours': _safe_decimal(row.get('total_hours')),
                'machine_hours': _safe_decimal(row.get('machine_hours')),
                'materials_total_qty': _safe_decimal(row.get('materials_total_qty')),
                'harvest_total_qty': _safe_decimal(row.get('harvest_total_qty')),
                'activities': row['activities'],
                'well_reading_total': _safe_decimal(row.get('well_reading_total')),
                'wells': sorted(
                    location_wells_map.get(row['location_id'], set())
                    | activity_well_map.get(row['location_id'], set())
                ) if row['location_id'] else [],
            }
            for row in location_rows
        ]
    
        well_metrics_map = {}
    
        def register_well(row, id_key, name_key):
            well_id = row.get(id_key)
            if not well_id:
                return
            loc_id = row.get('location_id')
            key = (well_id, loc_id)
            total_hours = _safe_decimal(row.get('total_hours'))
            total_reading = _safe_decimal(row.get('total_reading'))
            activities = row.get('activities') or 0
            entry = well_metrics_map.get(key)
            if entry:
                entry['total_hours'] += total_hours
                entry['total_reading'] += total_reading
                entry['activities'] += activities
                return
            well_metrics_map[key] = {
                'id': well_id,
                'name': row.get(name_key),
                'location_id': loc_id,
                'location_name': row.get('location__name'),
                'farm_id': row.get('location__farm_id'),
                'farm_name': row.get('location__farm__name'),
                'total_hours': total_hours,
                'total_reading': total_reading,
                'activities': activities,
            }
    
        for row in activity_qs.filter(well_asset__isnull=False, activity_locations__location__isnull=False).values(
            'well_asset_id',
            'well_asset__name',
            location_id=F('activity_locations__location_id'),
            location__name=F('activity_locations__location__name'),
            location__farm_id=F('activity_locations__location__farm_id'),
            location__farm__name=F('activity_locations__location__farm__name'),
        ).annotate(
            total_hours=Sum('days_spent'),
            total_reading=Sum('irrigation_details__well_reading'),
            activities=Count('id'),
        ):
            register_well(row, 'well_asset_id', 'well_asset__name')
    
        for row in activity_qs.filter(well_asset__isnull=True, asset__category='Well', activity_locations__location__isnull=False).values(
            'asset_id',
            'asset__name',
            location_id=F('activity_locations__location_id'),
            location__name=F('activity_locations__location__name'),
            location__farm_id=F('activity_locations__location__farm_id'),
            location__farm__name=F('activity_locations__location__farm__name'),
        ).annotate(
            total_hours=Sum('days_spent'),
            total_reading=Sum('irrigation_details__well_reading'),
            activities=Count('id'),
        ):
            register_well(row, 'asset_id', 'asset__name')
    
        wells_payload = sorted(
            well_metrics_map.values(),
            key=lambda item: (
                -(item['total_reading'] or 0),
                -(item['activities'] or 0),
                -(item['total_hours'] or 0),
            ),
        )[:10]
        
        harvest_rows = list(
            activity_qs
            .filter(product__isnull=False)
            .exclude(harvest_details__harvest_quantity__isnull=True)
            .values('product_id', 'product__name', 'product__pack_uom')
            .annotate(total_qty=Sum('harvest_details__harvest_quantity'), harvest_count=Count('id'))
            .order_by('-total_qty')[:10]
        )
        harvest_payload = []
        harvest_total_qty_calc = Decimal("0.0000")
        harvest_entries = 0
        for row in harvest_rows:
            qty = row['total_qty']
            if qty is None:
                continue
            total_qty = _safe_decimal(qty)
            harvest_total_qty_calc += total_qty
            harvest_entries += row['harvest_count']
            harvest_payload.append({
                'id': row['product_id'],
                'name': row['product__name'],
                'uom': row['product__pack_uom'] or '',
                'total_qty': total_qty,
                'entries': row['harvest_count'],
            })
    
        summary_payload = {
            'farms': list(Farm.objects.filter(id__in=farm_ids).values('id', 'name', 'region')) if farm_ids else [],
            'metrics': {
                'total_hours': _safe_decimal(metrics.get('total_hours')),
                'machine_hours': _safe_decimal(metrics.get('machine_hours')),
                'materials_total_qty': _safe_decimal(metrics.get('materials_total_qty')),
                'harvest_total_qty': _safe_decimal(metrics.get('harvest_total_qty')),
                'well_reading_total': _safe_decimal(metrics.get('well_reading_total')),
                'distinct_locations': activity_qs.filter(activity_locations__location__isnull=False).values('activity_locations__location_id').distinct().count(),
                'distinct_wells': distinct_wells,
                'harvest_entries': harvest_entries,
                'harvest_total_qty_calculated': harvest_total_qty_calc, 
            },
            'materials': materials_payload,
            'top_tasks': tasks_payload,
            'locations': locations_payload,
            'wells': wells_payload,
            'recent_logs': recent_logs_payload,
            'harvest': harvest_payload,
            'period': {
                'start': start.isoformat(),
                'end': end.isoformat(),
            },
            'filters': {
                'farms': farm_ids,
                'crop_id': context.crop_id,
                'task_id': context.task_id,
                'location_id': context.location_id,
                'season_id': context.season_id,
                'include_tree_inventory': context.include_tree_inventory,
                'section_scope': section_scope,
            },
        }
    
    
        if include_tree_inventory:
            try:
                tree_inventory_qs = LocationTreeStock.objects.select_related(
                    'location',
                    'location__farm',
                    'crop_variety',
                    'crop_variety__crop',
                    'productivity_status',
                )
                tree_inventory_qs = _limit_queryset_to_user_farms(tree_inventory_qs, request.user, 'location__farm_id__in')
                tree_inventory_qs, applied_tree_filters = _apply_tree_filters(tree_inventory_qs, tree_filters)
                total_current_trees = tree_inventory_qs.aggregate(total=Coalesce(Sum('current_tree_count', output_field=DecimalField()), Value(0, output_field=DecimalField())))['total'] or 0
                stocks_count = tree_inventory_qs.count()
                top_stocks = tree_inventory_qs.order_by('location__name', 'crop_variety__name')[:50]
                stocks_data = LocationTreeStockSerializer(top_stocks, many=True, context={'request': request}).data
                stock_ids = list(tree_inventory_qs.values_list('id', flat=True)[:200])
                events_qs = TreeStockEvent.objects.select_related(
                    'location_tree_stock',
                    'location_tree_stock__location',
                    'location_tree_stock__location__farm',
                    'location_tree_stock__crop_variety',
                    'location_tree_stock__crop_variety__crop',
                    'loss_reason',
                )
                if stock_ids:
                    events_qs = events_qs.filter(location_tree_stock_id__in=stock_ids)
                else:
                    events_qs = events_qs.none()
                events_data = TreeStockEventSerializer(
                    events_qs.order_by('-event_timestamp')[:10], many=True, context={'request': request}
                ).data
    
                inventory_payload = {
                    'total_current_tree_count': _safe_decimal(total_current_trees),
                    'stocks_count': stocks_count,
                    'stocks_sample': stocks_data,
                    'summary': stocks_data,
                    'recent_events': events_data,
                    'events': events_data,
                    'applied_filters': applied_tree_filters,
                }
    
                summary_payload['perennial_insights'] = {
                    'activity': {
                        'activities_count': int(tree_activity_stats.get('activities') or 0),
                        'trees_serviced': _safe_decimal(tree_activity_stats.get('trees_serviced')),
                        'net_tree_delta': _safe_decimal(tree_activity_stats.get('net_tree_delta')),
                        'loss_tree_delta': _safe_decimal(tree_activity_stats.get('loss_tree_delta')),
                        'gain_tree_delta': _safe_decimal(tree_activity_stats.get('gain_tree_delta')),
                    },
                    'inventory': inventory_payload,
                    'summary': inventory_payload['summary'],
                    'events': inventory_payload['events'],
                }
            except (DatabaseError, RuntimeError, ValueError, TypeError, AttributeError, KeyError) as e:
                logger.error(f"Error loading tree inventory: {e}")
                summary_payload['perennial_insights'] = {'error': str(e)}

        risk_zone_payload = []
        if 'risk_zone' in section_scope:
            risk_zone_payload = _build_risk_zone_payload(
                farm_id=farm_ids[0] if farm_ids else None,
                crop_id=context.crop_id,
                season_id=context.season_id,
            )

        # Limit details
        total_details = activity_qs.count()
        details_data = []
        details_meta = {
            'returned': 0,
            'limit': 0,
            'offset': 0,
            'has_more': False,
            'total': total_details,
        }
    
        if include_details:
            default_details_limit = 500
            details_limit = _coerce_int(request.query_params.get('details_limit')) or default_details_limit
            details_limit = max(1, min(details_limit, 2000))
            details_offset = _coerce_int(request.query_params.get('details_offset')) or 0
            details_offset = max(details_offset, 0)
    
            detailed_qs = activity_qs.order_by('-log__log_date', '-id')
            window_qs = detailed_qs[details_offset: details_offset + details_limit + 1]
            serializer = ActivitySerializer(window_qs, many=True, context={'request': request})
            details_data = serializer.data[:details_limit]
            has_more = len(serializer.data) > details_limit
            details_meta = {
                'returned': len(details_data),
                'limit': details_limit,
                'offset': details_offset,
                'has_more': has_more,
                'total': total_details,
            }
    
        return Response({
            'summary': summary_payload,
            'details': details_data,
            'details_meta': details_meta,
            'risk_zone': risk_zone_payload,
            'section_scope': section_scope,
        })
    except ValidationError as exc:
        return Response(getattr(exc, "detail", {"detail": str(exc)}), status=400)
    except PermissionDenied as exc:
        return Response({'detail': str(exc)}, status=403)
    except (DatabaseError, RuntimeError, ValueError, TypeError, AttributeError, KeyError) as exc:
        logger.exception(
            "advanced_report failed",
            extra={"actor_id": getattr(request.user, "id", None), "path": request.path},
        )
        return Response({'detail': f'تعذر إنشاء التقرير المتقدم: {exc}'}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_advanced_report_job(request):
    def _extract_params():
        extracted = {}
        extracted.update(request.query_params.dict())
        if isinstance(request.data, dict):
            extracted.update(request.data)
            return extracted
        if hasattr(request.data, "dict"):
            extracted.update(request.data.dict())
            return extracted
        if hasattr(request.data, "items"):
            extracted.update(dict(request.data.items()))
            return extracted
        raise ValidationError({"detail": "تعذر قراءة بيانات الطلب."})

    def _extract_single_farm_id(params: dict) -> int:
        raw_farm_id = params.get("farm_id") or params.get("farm")
        if raw_farm_id is None or str(raw_farm_id).strip() == "":
            # [AGRI-GUARDIAN] Auto-resolve first accessible farm when not specified
            return None
        raw_farm_id = str(raw_farm_id).split(",")[0].strip()
        if not raw_farm_id.isdigit():
            raise ValidationError({"farm_id": "farm_id must be a positive integer."})
        farm_id = int(raw_farm_id)
        if farm_id <= 0:
            raise ValidationError({"farm_id": "farm_id must be a positive integer."})
        return farm_id

    try:
        params = _extract_params()
        params["farm_id"] = _extract_single_farm_id(params)
        params.pop("farm", None)
        ReportingOrchestrationService._resolve_farm_for_alert(actor=request.user, params=params)

        job = ReportingOrchestrationService.create_advanced_report_request(
            actor=request.user,
            params=params,
        )

        inline_gen = _generate_advanced_report_inline
        if job.report_type == AsyncReportRequest.REPORT_PROFITABILITY:
            inline_gen = _generate_profitability_report_inline
        elif job.report_type == AsyncReportRequest.REPORT_COMMERCIAL_PDF:
            inline_gen = _generate_commercial_report_inline

        ReportingOrchestrationService.enqueue_or_fallback(
            actor=request.user,
            job=job,
            params=params,
            inline_generator=inline_gen,
        )

        return Response({
            'id': job.id,
            'status': job.status,
            'result_url': job.result_url,
            'requested_at': job.requested_at,
        }, status=202)
    except ValidationError as exc:
        return Response(getattr(exc, "detail", {"detail": str(exc)}), status=400)
    except PermissionDenied as exc:
        return Response({'detail': str(exc)}, status=403)
    except (ValueError, TypeError, LookupError, AttributeError, OperationalError, DatabaseError, ImportError, RuntimeError) as exc:
        logger.exception(
            "request_advanced_report_job failed",
            extra={"actor_id": getattr(request.user, "id", None), "path": request.path},
        )
        return Response({'detail': f'تعذر إنشاء طلب التقرير: {exc}'}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def advanced_report_job_status(request, request_id: int):
    try:
        job = AsyncReportRequest.objects.get(pk=request_id)
    except AsyncReportRequest.DoesNotExist:
        raise NotFound("طلب التقرير غير موجود")
    user = request.user
    if not (user.is_superuser or (job.created_by_id == user.id)):
        raise PermissionDenied("ليس لك صلاحية مراجعة هذا الطلب")
    job, stalled, _ = ReportingOrchestrationService.rescue_stalled_job(
        job=job,
        inline_generator=_resolve_inline_generator(job),
    )
    return Response({
        'id': job.id,
        'status': job.status,
        'result_url': job.result_url,
        'error_message': job.error_message,
        'requested_at': job.requested_at,
        'completed_at': job.completed_at,
        'stalled': stalled,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """
    ÙŠØ¹ÙŠØ¯ Ø¥Ø­ØµØ§Ø¦ÙŠØ§Øª Ø¹Ø§Ù„ÙŠØ© Ø§Ù„Ù…Ø³ØªÙˆÙ‰ Ù„Ù„ÙˆØ­Ø© Ø§Ù„Ù…Ø¹Ù„ÙˆÙ…Ø§Øª.
    [Agri-Guardian] Strict Tenant Isolation Applied.
    """
    try:
        from smart_agri.core.services.commercial_reporting_service import CommercialReportingService
        from django.core.cache import cache
        import hashlib

        # [Performance] Per-user cache key (2 min TTL) — respects tenant isolation
        user_id = request.user.id or "anon"
        filter_str = "|".join(str(request.GET.get(k, "")) for k in ("farm", "location", "crop_plan", "crop"))
        cache_key = f"dashboard_stats:{user_id}:{hashlib.md5(filter_str.encode()).hexdigest()}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        snapshot = CommercialReportingService.build_snapshot(request.GET.dict())

        result_data = {
            "active_plans": snapshot["pulse"]["active_plans"],
            "financials": {
                "revenue": snapshot["financials"]["revenue"],
                "cost": snapshot["financials"]["cost"],
                "distributable_surplus": snapshot["financials"]["net_profit"],
                # Compatibility key for existing clients pending migration.
                "net_profit": snapshot["financials"]["net_profit"],
                "currency": snapshot["currency"],
            },
            "yields": {
                "expected": snapshot["yields"]["expected"],
                "actual": snapshot["yields"]["actual"],
            },
            "trend": snapshot["trend"],
            "allocations": snapshot["allocations"],
            "grading": snapshot["grading"],
            "risk_zone": snapshot["risk_zone"],
            "alerts": _get_dashboard_alerts(request)
        }
        cache.set(cache_key, result_data, timeout=120)  # 2 minutes
        return Response(result_data)
    except ValidationError as exc:
        return Response(getattr(exc, "detail", {"detail": str(exc)}), status=400)
    except PermissionDenied as exc:
        return Response({'detail': str(exc)}, status=403)
    except (DatabaseError, RuntimeError, ValueError, TypeError, AttributeError, KeyError, ImportError) as exc:
        logger.exception(
            "dashboard_stats failed",
            extra={"actor_id": getattr(request.user, "id", None), "path": request.path},
        )
        return Response({'detail': f'تعذر تحميل إحصائيات اللوحة: {exc}'}, status=500)


def _get_dashboard_alerts(request=None):
    """
    ØªØ¬Ù…ÙŠØ¹ ØªÙ†Ø¨ÙŠÙ‡Ø§Øª Ø§Ù„Ù†Ø¸Ø§Ù… Ø§Ù„Ø­Ø±Ø¬Ø© Ù„Ù„ÙˆØ­Ø© Ø§Ù„Ù…Ø¹Ù„ÙˆÙ…Ø§Øª Ø§Ù„ØªÙ†ÙÙŠØ°ÙŠØ©.
    [Agri-Guardian] Tenancy Filter Applied.
    """
    alerts = []
    
    # 0. Tenancy Setup
    farm_ids = []
    if request and not request.user.is_superuser:
        farm_ids = user_farm_ids(request.user)

    def apply_farm_filter(qs, farm_field='farm_id', check_superuser=True):
        if check_superuser and request and request.user.is_superuser:
            return qs
        if farm_ids:
            return qs.filter(**{f"{farm_field}__in": farm_ids})
        return qs

    # 1. Pending cost allocation alerts
    from smart_agri.finance.models import ActualExpense
    pending_bills_qs = ActualExpense.objects.filter(is_allocated=False)
    pending_bills_qs = apply_farm_filter(pending_bills_qs, 'farm_id')
    pending_bills = pending_bills_qs.count()
    if pending_bills > 0:
        alerts.append({
            "level": "critical",
            "message": f"تنبيه: {pending_bills} مصاريف فعلية بانتظار التخصيص.",
            "action": "تشغيل تخصيص التكلفة"
        })

    # [AUDITOR FIX]: ÙƒØ´Ù Ø§Ù„Ø£Ø®Ø·Ø§Ø¡ Ø§Ù„Ø¥Ø¯Ø§Ø±ÙŠØ© ÙˆØ§Ù„Ù…Ø§Ù„ÙŠØ© Ø¨Ø¯Ù„Ø§Ù‹ Ù…Ù† Ø¥Ø®ÙØ§Ø¦Ù‡Ø§ (No passing through).
    from smart_agri.core.models.inventory import ItemInventory
    
    low_stock_qs = ItemInventory.objects.filter(
        qty__lt=F('item__reorder_level'),
        item__reorder_level__isnull=False
    )
    low_stock_qs = apply_farm_filter(low_stock_qs, 'farm_id')
    low_stock = low_stock_qs.count()
    
    if low_stock > 0:
        alerts.append({
            "level": "warning",
            "message": f"{low_stock} Ø¹Ù†Ø§ØµØ± Ø£Ù‚Ù„ Ù…Ù† Ù…Ø³ØªÙˆÙ‰ Ø¥Ø¹Ø§Ø¯Ø© Ø§Ù„Ø·Ù„Ø¨.",
            "action": "ÙØ­Øµ Ø§Ù„Ù…Ø®Ø²ÙˆÙ†"
        })

    # 3. Rejected daily logs
    from smart_agri.core.models.log import DailyLog
    rejected_logs_qs = DailyLog.objects.filter(status=DailyLog.STATUS_REJECTED)
    rejected_logs_qs = apply_farm_filter(rejected_logs_qs, 'farm_id')
    rejected_logs = rejected_logs_qs.count()
    if rejected_logs > 0:
        alerts.append({
            "level": "info",
            "message": f"{rejected_logs} سجلات يومية مرفوضة من قبل المشرفين.",
            "action": "مراجعة السجلات المرفوضة"
        })

    return alerts
