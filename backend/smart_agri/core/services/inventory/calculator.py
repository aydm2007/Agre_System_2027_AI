from dataclasses import dataclass
from typing import Optional

from smart_agri.core.models.activity import Activity
from smart_agri.core.models.tree import (
    LocationTreeStock,
    TreeStockEvent,
)
from smart_agri.core.services.inventory.policy import InventoryPolicy

@dataclass(frozen=True)
class TreeInventoryResult:
    stock: LocationTreeStock
    event: TreeStockEvent

class TreeEventCalculator:
    """
    منطق المجال النقي لأحداث مخزون الأشجار.
    مسؤول عن تحديد أنواع الأحداث والأعداد الناتجة.
    لا يتفاعل مع قاعدة البيانات (بدون آثار جانبية).
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
        delta: int,
        *,
        stock_changed: bool = False,
        existing_event: TreeStockEvent | None = None,
    ) -> str:
        if activity.task and getattr(activity.task, "is_harvest_task", False):
            return TreeStockEvent.HARVEST

        delta_value = int(delta or 0)

        if stock_changed and (
            delta_value != 0
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
