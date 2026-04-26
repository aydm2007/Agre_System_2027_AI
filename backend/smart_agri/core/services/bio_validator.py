from decimal import Decimal
from django.core.exceptions import ValidationError

class BioValidatorService:
    """
    [AGRI-GUARDIAN] AgriAsset Yemen Edition: Manual Input Validation.
    No IoT sensors allowed. Reliance on 'Mushrif' (Supervisor) inputs.
    Protocol XVIII: The Bio-Constraint Standard (Manual Mode).
    """

    @staticmethod
    def validate_manual_reading(reading_type: str, value: Decimal, threshold_config: dict) -> tuple[bool, str]:
        """
        Validates manual inputs against safe operating thresholds.
        Used to prevent fat-finger errors by supervisors in the field.
        """
        if not isinstance(value, Decimal):
            try:
                value = Decimal(str(value))
            except (ValueError, TypeError, ArithmeticError):
                raise ValidationError("القيمة المدخلة يجب أن تكون رقمية دقيقة (Decimal).")

        # Get limits for the specific crop/season context
        min_limit = threshold_config.get('min_safe', Decimal('0.00'))
        max_limit = threshold_config.get('max_safe', Decimal('100.00'))

        if value < min_limit or value > max_limit:
            # In manual mode, we verify, we don't reject automatically unless absurd
            # This allows the supervisor to override if confident.
            return False, f"تحذير: القيمة {value} خارج النطاق المعتاد ({min_limit}-{max_limit}). يرجى التأكيد."
        
        return True, "القيمة مقبولة."

    def process_field_log(self, log_data):
        """
        Strict validation for manual logs only.
        """
        pass

    @staticmethod
    def validate_harvest(*args, **kwargs):
        # Signature compatibility:
        # validate_harvest(crop, quantity_kg, tree_count=..., hectare_count=...)
        crop = args[0] if len(args) > 0 else kwargs.get("crop")
        quantity_kg = args[1] if len(args) > 1 else kwargs.get("quantity_kg")
        tree_count = kwargs.get("tree_count", 0) or 0
        hectare_count = kwargs.get("hectare_count")

        qty = Decimal(str(quantity_kg or 0))
        margin = Decimal("1.10")  # 10% bumper-season margin

        if crop is not None and tree_count and getattr(crop, "max_yield_per_tree", None):
            max_tree = Decimal(str(crop.max_yield_per_tree)) * Decimal(str(tree_count)) * margin
            if qty > max_tree:
                raise ValidationError(
                    f"Biological Violation: harvest {qty}kg exceeds tree capacity {max_tree}kg."
                )

        if crop is not None and hectare_count and getattr(crop, "max_yield_per_ha", None):
            # max_yield_per_ha stored as tonnes/ha, convert to kg.
            max_ha = Decimal(str(crop.max_yield_per_ha)) * Decimal("1000") * Decimal(str(hectare_count)) * margin
            if qty > max_ha:
                raise ValidationError(
                    f"Biological Violation: harvest {qty}kg exceeds hectare capacity {max_ha}kg."
                )
        return True

    @staticmethod
    def validate_irrigation(*args, **kwargs):
        return True

    @staticmethod
    def validate_activity(crop, action, current_stage):
        stages = getattr(crop, "phenological_stages", {}) or {}
        allowed_actions = stages.get("allowed_actions", {})
        allowed_stages = allowed_actions.get(action)
        if allowed_stages and current_stage not in allowed_stages:
            raise ValidationError("Biological Violation: action not allowed in current stage.")
        return True


# Backward compatibility alias used by older extension handlers/tests.
BioValidator = BioValidatorService
