from __future__ import annotations
import logging
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger(__name__)

# Canonical map of smart cards and their UI titles/metadata
CARD_METADATA = {
    "execution": {"title": "التنفيذ اليومي", "order": 10, "mode_visibility": "both", "data_source": "Activity"},
    "materials": {"title": "المواد والمستلزمات", "order": 20, "mode_visibility": "both", "data_source": "ActivityItem"},
    "labor": {"title": "العمالة اليومية", "order": 30, "mode_visibility": "both", "data_source": "ActivityEmployee"},
    "well": {"title": "قراءات الآبار", "order": 40, "mode_visibility": "both", "data_source": "ActivityIrrigation"},
    "machinery": {"title": "حركة المعدات", "order": 50, "mode_visibility": "both", "data_source": "ActivityMachineUsage"},
    "fuel": {"title": "استهلاك الديزل", "order": 60, "mode_visibility": "both", "data_source": "ActivityMachineUsage.fuel"},
    "perennial": {"title": "العمليات الحيوية", "order": 70, "mode_visibility": "both", "data_source": "Activity"},
    "harvest": {"title": "الحصاد والإنتاج", "order": 80, "mode_visibility": "both", "data_source": "ActivityHarvest"},
    "control": {"title": "الحوكمة والاعتماد", "order": 90, "mode_visibility": "both", "data_source": "Activity.control"},
    "variance": {"title": "تحليل الانحراف", "order": 100, "mode_visibility": "both", "data_source": "VarianceAlert"},
    "financial_trace": {"title": "الأثر المالي", "order": 110, "mode_visibility": "strict_only", "data_source": "FinancialLedger"},
}


def _populate_materials_metrics(card: dict, activity) -> dict:
    """Populates materials card metrics from actual ActivityItem records."""
    from smart_agri.core.models.activity import ActivityItem

    zero = Decimal("0")
    items_qs = ActivityItem.objects.filter(activity_id=activity.id).select_related('item', 'item__unit')

    actual_qty_total = sum(((i.qty or zero) for i in items_qs), zero)
    actual_cost_total = sum(((i.total_cost or zero) for i in items_qs), zero)

    line_items = [
        {
            "item_id": i.item_id,
            "item_name": i.item.name if i.item else str(i.item_id),
            "material_type": i.item.material_type if i.item else "OTHER",
            "material_type_display": i.item.get_material_type_display() if i.item else "أخرى",
            "actual_qty": str(i.qty or 0),
            "actual_cost": str(i.total_cost or 0),
            "uom": i.uom or "",
            "unit_symbol": (i.item.unit.symbol if i.item and i.item.unit else "") or i.uom or "",
            "unit_name": (i.item.unit.name if i.item and i.item.unit else "") or "",
            "planned_qty": str(i.planned_qty or 0) if hasattr(i, 'planned_qty') else "0",
            "planned_cost": "0",
            "qty_variance": "0",
            "cost_variance": "0",
        }
        for i in items_qs
    ]

    for line in line_items:
        planned = Decimal(line["planned_qty"])
        actual = Decimal(line["actual_qty"])
        if planned > 0:
            variance_pct = ((actual - planned) / planned * Decimal('100')).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)  # agri-guardian: decimal-safe
            line["qty_variance"] = str(actual - planned)
            line["qty_variance_pct"] = str(variance_pct)
        else:
            line["qty_variance_pct"] = "0"
    
    card["metrics"]["actual_qty"] = str(actual_qty_total)
    card["metrics"]["actual_cost"] = str(actual_cost_total)
    card["metrics"]["line_items"] = line_items
    card["status"] = "ready" if items_qs.exists() else "pending_data"
    
    return card



def _populate_irrigation_metrics(card: dict, activity) -> dict:
    """Populates well/irrigation card metrics from actual ActivityIrrigation records."""
    from smart_agri.core.models.activity import ActivityIrrigation
    try:
        irr = ActivityIrrigation.objects.get(activity_id=activity.id)
        card["metrics"]["water_volume"] = str(irr.water_volume or 0)
        card["metrics"]["well_reading"] = str(irr.well_reading or 0)
        card["metrics"]["is_solar_powered"] = getattr(irr, 'is_solar_powered', False)
        card["metrics"]["diesel_qty"] = str(getattr(irr, 'diesel_qty', 0) or 0)
        card["status"] = "ready"
    except ActivityIrrigation.DoesNotExist:
        card["status"] = "pending_data"
    return card


def _populate_labor_metrics(card: dict, activity) -> dict:
    """Populates labor card metrics including Hourly rates and Daily Achievement (Ingaz)."""
    from smart_agri.core.models.activity import ActivityEmployee
    zero = Decimal("0")
    emp_qs = ActivityEmployee.objects.filter(activity_id=activity.id).select_related('employee')

    total_cost = sum(((e.wage_cost or zero) for e in emp_qs), zero)
    total_achievement = sum(((e.achievement_qty or zero) for e in emp_qs), zero)
    
    # Aggregate UOM for summary (takes first available)
    achievement_uom = ""
    for e in emp_qs:
        if e.achievement_uom:
            achievement_uom = e.achievement_uom
            break

    card["metrics"]["total_cost"] = str(total_cost)
    card["metrics"]["total_achievement"] = str(total_achievement)
    card["metrics"]["achievement_uom"] = achievement_uom
    card["metrics"]["workers_count"] = emp_qs.count()
    
    card["metrics"]["line_items"] = [
        {
            "id": e.id,
            "label": str(e.employee) if e.employee else (e.labor_batch_label or "Casual Batch"),
            "is_hourly": e.is_hourly,
            "actual_cost": str(e.wage_cost or 0),
            "achievement_qty": str(e.achievement_qty or 0),
            "achievement_uom": e.achievement_uom or "",
            "hours": str(e.hours_worked or 0) if e.is_hourly else None,
            "workers": str(e.workers_count or 1)
        }
        for e in emp_qs
    ]
    
    card["status"] = "ready" if emp_qs.exists() else "pending_data"
    return card


def canonical_smart_card_stack(activity_payload: dict | None = None) -> list[dict]:
    """
    Deprecated proxy for old governance suites.
    """
    payload = activity_payload or {}
    stack = payload.get("smart_card_stack")
    if isinstance(stack, list):
        return stack
    return []


def build_smart_card_stack(activity) -> list[dict]:
    """
    Builds the canonical smart card stack for a given Activity instance, 
    derived primarily from the activity's task_contract_snapshot.
    """
    contract = activity.task_contract_snapshot
    if not contract and activity.task:
        contract = activity.task.get_effective_contract()
    
    if not contract:
        logger.warning(f"No task contract available for Activity {activity.id}. Returning empty stack.")
        return []

    smart_cards_config = contract.get("smart_cards", {})
    presentation = contract.get("presentation", {})
    card_order = presentation.get("card_order", list(CARD_METADATA.keys()))

    stack = []
    
    for card_key in card_order:
        card_config = smart_cards_config.get(card_key, {"enabled": False})
        meta = CARD_METADATA.get(card_key, {})
        
        # Base card structure
        card = {
            "card_key": card_key,
            "title": meta.get("title", card_key),
            "enabled": card_config.get("enabled", False),
            "order": meta.get("order", 999),
            "mode_visibility": meta.get("mode_visibility", "both"),
            "status": "pending_data",
            "metrics": {},
            "flags": [],
            "data_source": meta.get("data_source", "Unknown"),
            "policy": contract.get("control_rules", {}),
            "source_refs": [f"activity={activity.id}"]
        }
        
        if card["enabled"]:
            if card_key == "materials" and activity.id:
                card = _populate_materials_metrics(card, activity)
            elif card_key == "well" and activity.id:
                card = _populate_irrigation_metrics(card, activity)
            elif card_key == "labor" and activity.id:
                card = _populate_labor_metrics(card, activity)
            stack.append(card)

    return stack


def resolve_card_visibility(card: dict, farm_settings) -> bool:
    """
    Determines if a card should be visible based on FarmSettings constraints.
    """
    # Farm admin global toggle for smart cards in DailyLog
    if hasattr(farm_settings, "show_daily_log_smart_card") and not farm_settings.show_daily_log_smart_card:
        return False
        
    mode = getattr(farm_settings, "mode", "SIMPLE")
    visibility = card.get("mode_visibility", "both")
    
    if visibility == "strict_only" and mode != "STRICT":
        return False
        
    if visibility == "simple_only" and mode != "SIMPLE":
        return False
        
    return True


def scrub_disabled_cards(stack: list[dict], effective_task_contract: dict) -> list[dict]:
    """
    Scrubs completely disabled cards and sensitive fields if they aren't enabled by contract.
    """
    smart_cards_config = effective_task_contract.get("smart_cards", {})
    
    scrubbed = []
    for card in stack:
        card_key = card.get("card_key")
        is_enabled = smart_cards_config.get(card_key, {}).get("enabled", False)
        if is_enabled:
            scrubbed.append(card)
            
    return scrubbed
