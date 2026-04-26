from typing import Protocol, Optional, Iterable, Tuple, Any, Dict, Sequence
from datetime import date
from django.db import models

# Use quoting for forward references to avoid circular imports at runtime
# or strictly use TYPE_CHECKING if necessary. For Protocols, string forward refs are fine.

class IInventoryService(Protocol):
    """
    Protocol defining the contract for Tree Inventory operations.
    """
    
    def record_event_from_activity(
        self,
        activity: "Activity", 
        *,
        user=None,
        delta_change: Optional[int] = None,
        previous_delta: Optional[int] = None,
        activity_tree_count_change: Optional[int] = None,
        previous_activity_tree_count: Optional[int] = None,
        previous_location=None,
        previous_variety=None,
    ) -> Optional["TreeStockEvent"]:
        ...

    def reverse_activity(self, *, activity: "Activity", user=None) -> Any:
        ...

    def bulk_process_activities(self, activities: Iterable["Activity"], *, user=None) -> Tuple[int, list[int]]:
        ...

class ICostService(Protocol):
    """
    Protocol defining the contract for Costing operations.
    """
    
    def calculate_activity_cost(self, activity: "Activity", *, lock: bool = True) -> None:
        ...

    def calculate_bulk_costs(self, activities_queryset: models.QuerySet) -> int:
        ...
