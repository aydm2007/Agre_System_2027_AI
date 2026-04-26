from django.core.exceptions import ValidationError
from smart_agri.core.models import Activity

class InventoryPolicy:
    """
    Pure Logic layer for Tree Inventory Business Rules.
    Ensures that activities and adjustments comply with agricultural directives.
    """

    @staticmethod
    def is_tree_tracked(activity: Activity) -> bool:
        """Determines if an activity should impact tree inventory."""
        crop = activity.crop
        task = activity.task
        if not crop or not task:
            return False
        
        # Rule: Perennial procedures or explicit tree count requirements
        is_procedural = getattr(task, "is_perennial_procedure", False) or \
                        getattr(task, "requires_tree_count", False)
        
        return bool(is_procedural and activity.location and activity.variety)

    @staticmethod
    def validate_activity_for_stock(activity: Activity) -> None:
        """Validates that an activity has all necessary data for stock mutation."""
        errors = {}
        
        if not activity.location:
            errors["location"] = "Location must be specified for tree inventory updates."
        if not activity.variety:
            errors["variety"] = "Variety must be specified for tree inventory updates."
            
        # Rule: Loss requires a reason
        if (activity.tree_count_delta or 0) < 0 and not activity.tree_loss_reason:
            errors["tree_loss_reason"] = "A loss reason is required when recording a decrease in tree count."
            
        # Rule: Harvest requires quantity
        if activity.task and activity.task.is_harvest_task:
            harvest_qty = getattr(activity, "harvest_quantity", None)
            harvest_ext = getattr(activity, "harvest_details", None)
            if harvest_qty is None and (harvest_ext is None or harvest_ext.harvest_quantity is None):
                errors["harvest_quantity"] = "Harvest quantity is required for harvest tasks."
        
        if errors:
            raise ValidationError(errors)

    @staticmethod
    def validate_manual_adjustment(resulting_count, delta, reason) -> None:
        """Validates manual stock adjustment inputs."""
        if not (reason or "").strip():
             raise ValidationError({"reason": "A reason is required for manual adjustments."})
             
        if resulting_count is None and delta is None:
            raise ValidationError({"resulting_tree_count": "Must specify either resulting count or delta."})
        
        if resulting_count is not None and delta is not None:
             raise ValidationError({"delta": "Specify either resulting count OR delta, not both."})
             
        if resulting_count is not None and resulting_count < 0:
            raise ValidationError({"resulting_tree_count": "Resulting count cannot be negative."})
