"""
[AGRI-GUARDIAN] Pesticide Receiving Approval Gate.

Per AGENTS.md §152:
'Pesticide receiving must require technical approval from designated
agricultural engineer before stock admission.'

This service validates that pesticide items have engineer approval
before being accepted into inventory.
"""
import logging
from decimal import Decimal
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class PesticideApprovalService:
    """
    Validates pesticide receiving against engineer approval requirement.

    [AGENTS.md §152] Pesticide items require ag-engineer sign-off
    before they can be admitted to stock via GRN or StockMovement.
    """

    # Item categories that require engineer approval
    RESTRICTED_CATEGORIES = ['PESTICIDE', 'HERBICIDE', 'FUNGICIDE', 'INSECTICIDE']

    @staticmethod
    def requires_approval(item) -> bool:
        """
        Check if an item requires agricultural engineer approval.
        Returns True if item is in restricted categories.
        """
        category = getattr(item, 'category', None) or ''
        name_lower = (getattr(item, 'name', '') or '').lower()

        # Check explicit category
        if category.upper() in PesticideApprovalService.RESTRICTED_CATEGORIES:
            return True

        # Check name-based heuristic for Arabic/English pesticide terms
        pesticide_keywords = [
            'مبيد', 'مبيدات', 'pesticide', 'herbicide', 'fungicide',
            'insecticide', 'مبيد حشري', 'مبيد فطري', 'مبيد أعشاب',
        ]
        for keyword in pesticide_keywords:
            if keyword in name_lower:
                return True

        return False

    @staticmethod
    def validate_receiving(item, approved_by_engineer=False, engineer_user=None):
        """
        Validate that a pesticide item has proper engineer approval
        before being admitted to stock.

        Args:
            item: The inventory Item being received
            approved_by_engineer: Boolean flag from the receiving form
            engineer_user: The User object of the approving engineer

        Raises:
            ValidationError: if approval is required but not provided
        """
        if not PesticideApprovalService.requires_approval(item):
            return True

        if not approved_by_engineer:
            raise ValidationError(
                "استلام المبيدات يتطلب موافقة مسبقة من المهندس الزراعي المعتمد. "
                "يرجى الحصول على الموافقة الفنية قبل إدخال المادة للمخزن. "
                "[AGENTS.md §152: Pesticide Engineer Approval Gate]"
            )

        if engineer_user is None:
            raise ValidationError(
                "يجب تحديد المهندس الزراعي المعتمد الذي منح الموافقة الفنية."
            )

        # Log the approval for audit trail
        logger.info(
            f"[PESTICIDE GATE] Item '{item}' (ID={item.pk}) approved for receiving "
            f"by engineer '{engineer_user}' (ID={engineer_user.pk})"
        )

        return True

    @staticmethod
    def log_approval_audit(item, engineer_user, farm, notes=''):
        """
        Create an AuditLog entry for pesticide approval.
        [Axis 7] Auditability.
        """
        from smart_agri.core.models.log import AuditLog

        AuditLog.objects.create(
            model='Item',
            action='PESTICIDE_APPROVAL',
            object_id=str(item.pk),
            actor=str(engineer_user),
            old_payload={},
            new_payload={
                'item_id': item.pk,
                'item_name': str(item),
                'engineer_id': engineer_user.pk,
                'engineer_name': str(engineer_user),
                'farm_id': farm.pk if farm else None,
                'notes': notes,
            }
        )
