from dataclasses import dataclass
from typing import Optional
from decimal import Decimal
from smart_agri.core.models import Activity, TreeStockEvent, LocationTreeStock

@dataclass(frozen=True)
class TreeInventoryResult:
    stock: LocationTreeStock
    event: TreeStockEvent

class TreeEventCalculator:
    """
    Pure Domain Logic for Tree Inventory Events.
    Responsible for determining Event Types and Resulting Counts.
    Does NOT interact with the database (no Side Effects).
    Actuals-only: no estimated time fields or legacy crop variety shortcuts.
    """

    def resolve_resulting_count(
        self,
        *,
        activity: Activity,
        stock: LocationTreeStock,
        existing_event: TreeStockEvent | None,
        activity_tree_count_change: Optional[int],
        previous_activity_tree_count: Optional[int],
    ) -> int:
        if activity_tree_count_change is not None:
            if previous_activity_tree_count is not None:
                base = previous_activity_tree_count or 0
            elif existing_event and existing_event.resulting_tree_count is not None:
                base = existing_event.resulting_tree_count
            else:
                base = stock.current_tree_count or 0
            return base + activity_tree_count_change

        if activity.activity_tree_count is not None and (
            existing_event is not None or previous_activity_tree_count is not None
        ):
            return activity.activity_tree_count

        return stock.current_tree_count or 0

    def compute_event_type(
        self,
        activity: Activity,
        delta: int | Decimal, # Updated type hint
        *,
        stock_changed: bool = False,
        existing_event: TreeStockEvent | None = None,
    ) -> str:
        # [Agri-Guardian] Safe handling for Decimal inputs
        from decimal import Decimal
        
        if activity.task and getattr(activity.task, "is_harvest_task", False):
            return TreeStockEvent.HARVEST
            
        delta_value = delta if delta is not None else 0
        
        # Compare carefully (Decimal(0) == 0 is True, but good to be explicit)
        is_zero = delta_value == 0
        is_positive = delta_value > 0
        
        if stock_changed and (
            not is_zero
            or (existing_event and (existing_event.tree_count_delta or 0) != 0)
        ):
            return TreeStockEvent.TRANSFER

        if delta_value > 0:
            return TreeStockEvent.PLANTING
        if delta_value < 0:
            return TreeStockEvent.LOSS

        if getattr(activity, "water_volume", None) or getattr(activity, "fertilizer_quantity", None):
            return TreeStockEvent.ADJUSTMENT

        task = activity.task
        if task and (
            getattr(task, "requires_tree_count", False)
            or getattr(task, "is_perennial_procedure", False)
        ):
            return TreeStockEvent.ADJUSTMENT

        return TreeStockEvent.ADJUSTMENT
