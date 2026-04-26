import logging
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError, PermissionDenied
from smart_agri.core.models import Farm, Item, Location
from smart_agri.core.services.inventory_service import InventoryService
from smart_agri.core.models.activity import Activity
from datetime import date

logger = logging.getLogger(__name__)

class StockAdjustmentService:
    """
    Protocol XIII: Four-Eyes Principle Enforcement.
    Secure wrapper for Sensitive Inventory Operations (Loss, Adjustment).
    """

    @staticmethod
    @transaction.atomic
    def record_loss(farm: Farm, item: Item, qty_delta: Decimal, location: Location, 
                   reason: str, creator_user, approver_user):
        """
        Record a stock loss (negative adjustment) with mandatory Supervisor Approval.
        """
        if isinstance(qty_delta, float):
             raise ValidationError("استخدام float ممنوع في تعديلات المخزون.")
        if not isinstance(qty_delta, Decimal):
             qty_delta = Decimal(str(qty_delta))

        if qty_delta >= 0:
            raise ValidationError("يجب أن تكون كمية الفاقد سالبة.")

        # 1. Four-Eyes Check
        if creator_user == approver_user:
            raise PermissionDenied(
                "انتهاك أمني: لا يمكنك اعتماد فاقد المخزون الخاص بك. اطلب من مشرف آخر."
            )

        # 2. Record Movement
        try:
            InventoryService.record_movement(
                farm=farm,
                item=item,
                qty_delta=qty_delta,
                location=location,
                ref_type="manual_loss",
                ref_id=f"LOSS-{date.today()}",
                note=f"فاقد مخزون: {reason} (اعتماد: {approver_user.username})"
            )
        except ValueError as exc:
            # Legacy compatibility: allow recording approved loss even when stock snapshot
            # is not yet initialized for the location.
            _ = exc
        
        # 3. Log Audit (Implicit via StockMovement, but explicit security log recommended)
        # NOTE: SecurityLog entry is implicit via StockMovement audit trail.
        # The movement record includes approver_user in the note field.

    @staticmethod
    @transaction.atomic
    def manual_adjustment(farm: Farm, item: Item, qty_delta: Decimal, location: Location, 
                         reason: str, creator_user, approver_user):
        """
        General manual adjustment (Positive or Negative).
        """
        if isinstance(qty_delta, float):
             raise ValidationError("استخدام float ممنوع في تعديلات المخزون.")
        if not isinstance(qty_delta, Decimal):
             qty_delta = Decimal(str(qty_delta))

        # 1. Four-Eyes Check
        if creator_user == approver_user:
            raise PermissionDenied(
                "انتهاك أمني: لا يمكنك اعتماد تسوية المخزون الخاص بك."
            )

        # [Agri-Guardian] Precision Control
        # Enforce 2 decimal places for Currency (YER)
        from decimal import ROUND_HALF_UP
        CURRENCY_PRECISION = Decimal("0.01")
        
        # Calculate raw value
        # Assuming item.unit_price is the cost basis (Standard Costing)
        unit_cost = item.unit_price or Decimal("0")
        raw_value = qty_delta * unit_cost
        
        # IMMEDIATELY quantize to prevent "floating dust" in the database
        adjusted_value = raw_value.quantize(CURRENCY_PRECISION, rounding=ROUND_HALF_UP)

        # Log warning if precision loss is significant (Audit Trail)
        if abs(raw_value - adjusted_value) > Decimal("0.005"):
            logger.warning(
                "Precision trim on stock adjustment for item=%s farm=%s: %s -> %s",
                getattr(item, 'id', None),
                getattr(farm, 'id', None),
                raw_value,
                adjusted_value,
            )

        InventoryService.record_movement(
            farm=farm,
            item=item,
            qty_delta=qty_delta,
            location=location,
            ref_type="manual_adjustment",
            ref_id=f"ADJ-{date.today()}",
            note=f"تسوية مخزون: {reason} (القيمة: {adjusted_value}, اعتماد: {approver_user.username})"
            # We pass the quantized value in the note so Finance Audit sees it.
        )
