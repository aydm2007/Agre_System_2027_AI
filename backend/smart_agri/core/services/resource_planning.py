from collections import defaultdict, deque
from decimal import Decimal
from django.core.cache import cache
from django.db.models import Q, Sum

from ..models import (
    ActivityItem,
    Crop,
    CropMaterial,
    Item,
    Unit,
    UnitConversion,
)

# CACHE KEY
# CACHE KEY
CONVERSION_GRAPH_CACHE_KEY = "core_conversion_graph_v1"
# AGRI-GUARDIAN: Reduced timeout from 3600 to 300.
# Context: Manual corrections happen frequently; stale data causes wrong planning.
CONVERSION_GRAPH_TIMEOUT = 300  # 5 minutes

class ConversionError(Exception):
    """Raised when unit conversion path is not found."""
    pass

def _build_conversion_graph():
    # Performance Fix: Cache the graph construction
    cached_graph = cache.get(CONVERSION_GRAPH_CACHE_KEY)
    if cached_graph:
        return cached_graph

    graph = defaultdict(list)
    conversions = UnitConversion.objects.filter(deleted_at__isnull=True)
    for conversion in conversions:
        if conversion.multiplier and conversion.multiplier > 0:
            multiplier = Decimal(conversion.multiplier)
            graph[conversion.from_unit_id].append((conversion.to_unit_id, multiplier))
            try:
                from decimal import getcontext
                inverse = getcontext().divide(Decimal('1'), multiplier)
            except (ArithmeticError, ZeroDivisionError):
                inverse = None
            if inverse:
                graph[conversion.to_unit_id].append((conversion.from_unit_id, inverse))
    
    # Store in cache
    cache.set(CONVERSION_GRAPH_CACHE_KEY, dict(graph), CONVERSION_GRAPH_TIMEOUT)
    return graph


def _resolve_unit_by_code(code_to_unit, code):
    if not code:
        return None
    normalised = str(code).strip().lower()
    return code_to_unit.get(normalised)


def _find_multiplier(graph, start, target):
    if start is None or target is None:
        return None
    if start == target:
        return Decimal('1')
    visited = set()
    queue = deque([(start, Decimal('1'))])
    while queue:
        unit_id, factor = queue.popleft()
        if unit_id == target:
            return factor
        if unit_id in visited:
            continue
        visited.add(unit_id)
        for neighbour, weight in graph.get(unit_id, []):
            if neighbour not in visited:
                queue.append((neighbour, factor * weight))
    return None


def _convert_quantity(graph, value, from_unit_id, to_unit_id):
    """
    Converts quantity between units. 
    Strict Mode: RAISES Error if conversion path not found.
    """
    if value is None:
        return None
    if from_unit_id == to_unit_id or to_unit_id is None:
        return Decimal(value)
    
    multiplier = _find_multiplier(graph, from_unit_id, to_unit_id)
    if multiplier is None:
        # STRICT FIX: Do not return original value silently.
        raise ConversionError(
            f"Financial Integrity Error: No conversion path found from UnitID {from_unit_id} to UnitID {to_unit_id}. "
            f"Cannot strictly value this resource."
        )
        
    return Decimal(value) * multiplier


def build_resource_overview(user, *, farm_ids=None, crop_ids=None, start_date=None, end_date=None):
    farm_ids = farm_ids or []
    crop_filter = crop_ids or []

    crop_queryset = Crop.objects.filter(deleted_at__isnull=True)
    if crop_filter:
        crop_queryset = crop_queryset.filter(id__in=crop_filter)
    if farm_ids:
        crop_queryset = crop_queryset.filter(farm_links__farm_id__in=farm_ids, farm_links__deleted_at__isnull=True)
    crop_queryset = crop_queryset.distinct().order_by('name')

    crops = list(crop_queryset)
    if not crops:
        return []

    crop_ids = [crop.id for crop in crops]
    items_map = {item.id: item for item in Item.objects.filter(deleted_at__isnull=True, crop_material_links__crop_id__in=crop_ids).distinct()}
    unit_map = {unit.id: unit for unit in Unit.objects.filter(deleted_at__isnull=True)}
    code_to_unit = {unit.code.lower(): unit for unit in unit_map.values() if unit.code}

    graph = _build_conversion_graph()

    materials = (
        CropMaterial.objects.filter(crop_id__in=crop_ids, deleted_at__isnull=True)
        .values('crop_id', 'item_id', 'recommended_unit_id', 'recommended_uom')
        .annotate(total_recommended=Sum('recommended_qty'))
    )

    recommended_map = defaultdict(dict)
    for entry in materials:
        recommended_map[entry['crop_id']][entry['item_id']] = {
            'recommended_qty': Decimal(entry['total_recommended'] or 0),
            'recommended_unit_id': entry['recommended_unit_id'],
            'recommended_uom': entry['recommended_uom'] or '',
        }

    activity_filters = Q(activity__deleted_at__isnull=True, activity__log__deleted_at__isnull=True, activity__crop_id__in=crop_ids)
    if farm_ids:
        activity_filters &= Q(activity__log__farm_id__in=farm_ids)
    if start_date:
        activity_filters &= Q(activity__log__log_date__gte=start_date)
    if end_date:
        activity_filters &= Q(activity__log__log_date__lte=end_date)

    actual_items = (
        ActivityItem.objects.filter(activity_filters)
        .values('activity__crop_id', 'item_id', 'uom')
        .annotate(total_qty=Sum('qty'))
    )

    actual_map = defaultdict(dict)
    for entry in actual_items:
        row = actual_map[entry['activity__crop_id']].setdefault(entry['item_id'], {'qty': Decimal('0'), 'uoms': []})
        qty = entry['total_qty'] or 0
        row['qty'] += Decimal(qty)
        if entry['uom']:
            row['uoms'].append(entry['uom'])

    overview = []
    for crop in crops:
        crop_entry = {
            'crop': {
                'id': crop.id,
                'name': crop.name,
                'mode': crop.mode,
                'is_perennial': crop.is_perennial,
            },
            'materials': [],
            'totals': {
                'recommended_cost': Decimal('0'),
                'actual_cost': Decimal('0'),
            },
        }

        material_rows = recommended_map.get(crop.id, {})
        actual_rows = actual_map.get(crop.id, {})
        item_ids = set(material_rows.keys()) | set(actual_rows.keys())

        for item_id in sorted(item_ids):
            item = items_map.get(item_id)
            if not item:
                continue

            item_unit_id = item.unit_id
            recommended = material_rows.get(item_id, {})
            recommended_qty = recommended.get('recommended_qty') or Decimal('0')
            recommended_unit_id = recommended.get('recommended_unit_id') or item_unit_id
            actual_data = actual_rows.get(item_id, {})
            actual_qty = actual_data.get('qty') or Decimal('0')
            actual_unit_id = None

            if actual_data.get('uoms'):
                for uom_code in actual_data['uoms']:
                    unit = _resolve_unit_by_code(code_to_unit, uom_code)
                    if unit:
                        actual_unit_id = unit.id
                        break

            # STRICT CONVERSION: May Raise ConversionError which should be handled or bubbled up
            # For the overview report, we might want to catch it or let it fail 500 to alert admin.
            # Letting it fail 500 is consistent with "Loud Failure" policy.
            recommended_qty_converted = _convert_quantity(graph, recommended_qty, recommended_unit_id, item_unit_id)
            actual_qty_converted = _convert_quantity(graph, actual_qty, actual_unit_id, item_unit_id)

            unit_price = Decimal(item.unit_price or 0)
            recommended_cost = (recommended_qty_converted or Decimal('0')) * unit_price
            actual_cost = (actual_qty_converted or Decimal('0')) * unit_price

            crop_entry['totals']['recommended_cost'] += recommended_cost
            crop_entry['totals']['actual_cost'] += actual_cost

            unit_symbol = None
            if item_unit_id and unit_map.get(item_unit_id):
                unit_symbol = unit_map[item_unit_id].symbol or unit_map[item_unit_id].code

            crop_entry['materials'].append({
                'item_id': item.id,
                'item_name': item.name,
                'group': item.group,
                'unit_symbol': unit_symbol or item.uom,
                'recommended_qty': recommended_qty_converted,
                'actual_qty': actual_qty_converted,
                'recommended_cost': recommended_cost,
                'actual_cost': actual_cost,
                'variance_qty': (actual_qty_converted or Decimal('0')) - (recommended_qty_converted or Decimal('0')),
                'variance_cost': actual_cost - recommended_cost,
            })

        overview.append(crop_entry)

    return overview
