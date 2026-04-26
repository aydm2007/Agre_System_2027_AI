"""
Read-only compatibility ViewSets for endpoints that the frontend still expects.

These endpoints no longer return empty placeholders. Instead they provide
backward-compatible, governed read models derived from the canonical domain
objects already present in the system.
"""
from decimal import Decimal
import logging

from django.db.models import Max, Q, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from smart_agri.core.api.permissions import _ensure_user_has_farm_access, user_farm_ids

logger = logging.getLogger(__name__)
ZERO = Decimal("0.0000")


def _parse_csv_ids(raw_value):
    if raw_value in [None, "", "null", "undefined"]:
        return []
    return [int(x) for x in str(raw_value).split(',') if str(x).strip().isdigit()]


def _resolve_target_farm_ids(request):
    farm_param = request.query_params.get('farm_id') or request.query_params.get('farm')
    target_farm_ids = []
    if farm_param:
        parsed = _parse_csv_ids(farm_param)
        if not parsed:
            return []
        for farm_id in parsed:
            _ensure_user_has_farm_access(request.user, farm_id)
        return parsed
    if request.user.is_superuser:
        return []
    return user_farm_ids(request.user)


class StubServiceProviderViewSet(viewsets.ViewSet):
    """
    Backward-compatible supplier/provider dashboard.

    The legacy ServiceProvider model was removed, but operationally the UI still
    benefits from a provider list. We derive that list from Purchase Orders and
    Supplier Settlements so the endpoint remains useful instead of returning an
    empty stub.
    """

    permission_classes = [IsAuthenticated]

    def list(self, request):
        from smart_agri.inventory.models import PurchaseOrder
        from smart_agri.finance.models_supplier_settlement import SupplierSettlement

        target_farm_ids = _resolve_target_farm_ids(request)
        purchase_orders = PurchaseOrder.objects.filter(deleted_at__isnull=True)
        settlements = SupplierSettlement.objects.filter(deleted_at__isnull=True).select_related('purchase_order')

        if target_farm_ids:
            purchase_orders = purchase_orders.filter(farm_id__in=target_farm_ids)
            settlements = settlements.filter(farm_id__in=target_farm_ids)
        elif not request.user.is_superuser:
            return Response([])

        vendor_filter = (request.query_params.get('q') or request.query_params.get('vendor') or '').strip()
        if vendor_filter:
            purchase_orders = purchase_orders.filter(vendor_name__icontains=vendor_filter)
            settlements = settlements.filter(purchase_order__vendor_name__icontains=vendor_filter)

        purchase_summary = {}
        for po in purchase_orders.values('vendor_name', 'status', 'total_amount', 'order_date'):
            vendor_name = po['vendor_name']
            entry = purchase_summary.setdefault(
                vendor_name,
                {
                    'vendor_name': vendor_name,
                    'purchase_orders_count': 0,
                    'approved_orders': 0,
                    'total_order_amount': ZERO,
                    'last_order_date': None,
                },
            )
            entry['purchase_orders_count'] += 1
            entry['approved_orders'] += 1 if po['status'] == 'APPROVED' else 0
            entry['total_order_amount'] += po['total_amount'] or ZERO
            if po['order_date'] and (entry['last_order_date'] is None or po['order_date'] > entry['last_order_date']):
                entry['last_order_date'] = po['order_date']

        settlement_summary = {}
        for row in settlements.values(
            'purchase_order__vendor_name',
            'payable_amount',
            'paid_amount',
            'due_date',
            'status',
        ):
            vendor_name = row['purchase_order__vendor_name'] or '—'
            entry = settlement_summary.setdefault(
                vendor_name,
                {
                    'settlements_count': 0,
                    'payable_total': ZERO,
                    'paid_total': ZERO,
                    'open_balance': ZERO,
                    'overdue_count': 0,
                    'last_due_date': None,
                    'risk_status': 'normal',
                },
            )
            payable = row['payable_amount'] or ZERO
            paid = row['paid_amount'] or ZERO
            balance = payable - paid
            entry['settlements_count'] += 1
            entry['payable_total'] += payable
            entry['paid_total'] += paid
            entry['open_balance'] += balance
            if row['due_date'] and balance > ZERO and row['status'] not in {'PAID'}:
                from django.utils import timezone
                if row['due_date'] < timezone.localdate():
                    entry['overdue_count'] += 1
                    entry['risk_status'] = 'warning'
            if row['status'] == 'REJECTED':
                entry['risk_status'] = 'critical'
            if row['due_date'] and (entry['last_due_date'] is None or row['due_date'] > entry['last_due_date']):
                entry['last_due_date'] = row['due_date']

        vendor_names = sorted(set(purchase_summary) | set(settlement_summary))
        results = []
        for vendor_name in vendor_names:
            purchase_info = purchase_summary.get(vendor_name, {})
            settlement_info = settlement_summary.get(vendor_name, {})
            results.append(
                {
                    'vendor_name': vendor_name,
                    'purchase_orders_count': purchase_info.get('purchase_orders_count', 0),
                    'approved_orders': purchase_info.get('approved_orders', 0),
                    'total_order_amount': str(purchase_info.get('total_order_amount', ZERO)),
                    'last_order_date': purchase_info.get('last_order_date'),
                    'settlements_count': settlement_info.get('settlements_count', 0),
                    'payable_total': str(settlement_info.get('payable_total', ZERO)),
                    'paid_total': str(settlement_info.get('paid_total', ZERO)),
                    'open_balance': str(settlement_info.get('open_balance', ZERO)),
                    'overdue_count': settlement_info.get('overdue_count', 0),
                    'last_due_date': settlement_info.get('last_due_date'),
                    'risk_status': settlement_info.get('risk_status', 'normal'),
                }
            )

        return Response(results)

    def create(self, request):
        logger.warning(
            "[COMPAT] ServiceProvider.create attempted by user %s - read-only compatibility surface",
            request.user.username,
        )
        return Response(
            {'detail': 'واجهة مقدمي الخدمات أصبحت قراءةً فقط وتعتمد على أوامر الشراء وتسويات الموردين.'},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )

    def retrieve(self, request, pk=None):
        return Response({'detail': 'غير مدعوم على هذه الواجهة التوافقية.'}, status=404)

    def update(self, request, pk=None):
        return Response({'detail': 'واجهة قراءة فقط.'}, status=405)

    def partial_update(self, request, pk=None):
        return Response({'detail': 'واجهة قراءة فقط.'}, status=405)

    def destroy(self, request, pk=None):
        return Response({'detail': 'واجهة قراءة فقط.'}, status=405)


class StubMaterialCardViewSet(viewsets.ViewSet):
    """
    Material intelligence cards.

    The endpoint used to be a stub; it now exposes a governed read model that
    bridges agronomy planning, stock on hand, consumption, and movement trace.
    """

    permission_classes = [IsAuthenticated]

    def list(self, request):
        from smart_agri.core.models import ActivityItem, CropMaterial, Item, ItemInventory, StockMovement

        target_farm_ids = _resolve_target_farm_ids(request)
        if target_farm_ids == [] and not request.user.is_superuser and not user_farm_ids(request.user):
            return Response([])

        item_filter = _parse_csv_ids(request.query_params.get('item_id') or request.query_params.get('item'))
        crop_filter = _parse_csv_ids(request.query_params.get('crop_id') or request.query_params.get('crop'))
        group_filter = (request.query_params.get('group') or '').strip()

        items_qs = Item.objects.filter(deleted_at__isnull=True)
        crop_materials_qs = CropMaterial.objects.filter(deleted_at__isnull=True).select_related('crop', 'item', 'recommended_unit')
        inventories_qs = ItemInventory.objects.filter(deleted_at__isnull=True).select_related('item', 'item__unit')
        movements_qs = StockMovement.objects.filter(deleted_at__isnull=True)
        activity_items_qs = ActivityItem.objects.filter(deleted_at__isnull=True)

        if group_filter:
            items_qs = items_qs.filter(group=group_filter)
            crop_materials_qs = crop_materials_qs.filter(item__group=group_filter)
            inventories_qs = inventories_qs.filter(item__group=group_filter)
            movements_qs = movements_qs.filter(item__group=group_filter)
            activity_items_qs = activity_items_qs.filter(item__group=group_filter)
        if item_filter:
            items_qs = items_qs.filter(id__in=item_filter)
            crop_materials_qs = crop_materials_qs.filter(item_id__in=item_filter)
            inventories_qs = inventories_qs.filter(item_id__in=item_filter)
            movements_qs = movements_qs.filter(item_id__in=item_filter)
            activity_items_qs = activity_items_qs.filter(item_id__in=item_filter)
        if crop_filter:
            crop_materials_qs = crop_materials_qs.filter(crop_id__in=crop_filter)
            items_qs = items_qs.filter(id__in=crop_materials_qs.values_list('item_id', flat=True))

        if target_farm_ids:
            inventories_qs = inventories_qs.filter(farm_id__in=target_farm_ids)
            movements_qs = movements_qs.filter(farm_id__in=target_farm_ids)
            activity_items_qs = activity_items_qs.filter(activity__log__farm_id__in=target_farm_ids)
            crop_ids = crop_materials_qs.values_list('crop_id', flat=True)
            # Keep catalog relevant to farms that actually have the crop when possible.
            from smart_agri.core.models import FarmCrop
            relevant_crop_ids = FarmCrop.objects.filter(
                farm_id__in=target_farm_ids,
                deleted_at__isnull=True,
                crop_id__in=crop_ids,
            ).values_list('crop_id', flat=True)
            crop_materials_qs = crop_materials_qs.filter(crop_id__in=relevant_crop_ids)
        elif not request.user.is_superuser:
            return Response([])

        inventory_rows = inventories_qs.values('item_id').annotate(
            on_hand_qty=Coalesce(Sum('qty'), Value(ZERO)),
        )
        inventory_map = {row['item_id']: row['on_hand_qty'] or ZERO for row in inventory_rows}

        movement_rows = movements_qs.values('item_id').annotate(
            inbound_qty=Coalesce(Sum('qty_delta', filter=Q(qty_delta__gt=0)), Value(ZERO)),
            outbound_qty=Coalesce(Sum('qty_delta', filter=Q(qty_delta__lt=0)), Value(ZERO)),
            last_movement_at=Max('created_at'),
        )
        movement_map = {}
        for row in movement_rows:
            outbound = abs(row['outbound_qty'] or ZERO)
            movement_map[row['item_id']] = {
                'inbound_qty': row['inbound_qty'] or ZERO,
                'outbound_qty': outbound,
                'last_movement_at': row['last_movement_at'],
            }

        usage_rows = activity_items_qs.values('item_id').annotate(
            consumed_qty=Coalesce(Sum('qty'), Value(ZERO)),
            consumed_cost=Coalesce(Sum('total_cost'), Value(ZERO)),
            last_consumed_at=Max('created_at'),
        )
        usage_map = {row['item_id']: row for row in usage_rows}

        crop_material_map = {}
        for row in crop_materials_qs.values(
            'item_id',
            'crop_id',
            'crop__name',
            'recommended_qty',
            'recommended_uom',
        ):
            entry = crop_material_map.setdefault(
                row['item_id'],
                {
                    'recommended_qty_total': ZERO,
                    'crop_links': [],
                },
            )
            entry['recommended_qty_total'] += row['recommended_qty'] or ZERO
            entry['crop_links'].append(
                {
                    'crop_id': row['crop_id'],
                    'crop_name': row['crop__name'],
                    'recommended_qty': str(row['recommended_qty'] or ZERO),
                    'recommended_uom': row['recommended_uom'],
                }
            )

        candidate_item_ids = set(inventory_map) | set(movement_map) | set(usage_map) | set(crop_material_map)
        if item_filter:
            candidate_item_ids |= set(item_filter)
        items = items_qs.filter(id__in=candidate_item_ids).select_related('unit').order_by('group', 'name')

        results = []
        for item in items:
            on_hand_qty = inventory_map.get(item.id, ZERO)
            movement_info = movement_map.get(item.id, {})
            usage_info = usage_map.get(item.id, {})
            crop_info = crop_material_map.get(item.id, {'recommended_qty_total': ZERO, 'crop_links': []})
            reorder_level = item.reorder_level or ZERO
            coverage_gap = on_hand_qty - crop_info['recommended_qty_total']
            results.append(
                {
                    'item': {
                        'id': item.id,
                        'name': item.name,
                        'group': item.group,
                        'uom': item.uom,
                        'unit_price': str(item.unit_price or ZERO),
                        'reorder_level': str(reorder_level),
                        'requires_batch_tracking': item.requires_batch_tracking,
                        'phi_days': item.phi_days,
                    },
                    'inventory_metrics': {
                        'on_hand_qty': str(on_hand_qty),
                        'inbound_qty': str(movement_info.get('inbound_qty', ZERO)),
                        'outbound_qty': str(movement_info.get('outbound_qty', ZERO)),
                        'last_movement_at': movement_info.get('last_movement_at'),
                        'low_stock': on_hand_qty < reorder_level if reorder_level else False,
                    },
                    'usage_metrics': {
                        'consumed_qty': str(usage_info.get('consumed_qty', ZERO) or ZERO),
                        'consumed_cost': str(usage_info.get('consumed_cost', ZERO) or ZERO),
                        'last_consumed_at': usage_info.get('last_consumed_at'),
                    },
                    'planning_metrics': {
                        'recommended_qty_total': str(crop_info['recommended_qty_total']),
                        'coverage_gap': str(coverage_gap),
                        'crop_links': crop_info['crop_links'],
                    },
                    'health_flags': {
                        'needs_restock': on_hand_qty < reorder_level if reorder_level else False,
                        'under_planned_stock': on_hand_qty < crop_info['recommended_qty_total'],
                        'batch_sensitive': item.requires_batch_tracking,
                    },
                }
            )

        return Response(results)
