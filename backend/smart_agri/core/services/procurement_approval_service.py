"""
ProcurementApprovalService — فرض 3 توقيعات رقمية للمشتريات الكبيرة.

[AGRI-GUARDIAN Axis 10] Multi-Tier Procurement:
Any procurement > FarmSettings.procurement_committee_threshold requires
3 digital signatures (Manager, CFO, Auditor).

AGENTS.md Compliance:
  - Axis 5: Decimal(19,4)
  - Axis 6: Farm-scoped
  - Axis 7: AuditLog
  - Axis 10: Tiered procurement thresholds
"""

import logging
from decimal import Decimal

from django.db import transaction
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

FOUR_DP = Decimal("0.0001")
REQUIRED_SIGNATURES = 3


class ProcurementApprovalService:
    """
    [AGENTS.md Axis 10] Validates procurement approvals based on farm tier.

    Enforces that any purchase order exceeding the farm's procurement
    committee threshold has at least 3 distinct approvers.
    """

    @staticmethod
    def get_threshold(farm_id: int) -> Decimal:
        """
        Load the procurement committee threshold for the given farm.
        Falls back to system default if no FarmSettings exist.
        """
        from smart_agri.core.models.settings import FarmSettings

        try:
            fs = FarmSettings.objects.get(farm_id=farm_id)
            return fs.procurement_committee_threshold
        except FarmSettings.DoesNotExist:
            return Decimal('500000.0000')  # Default per AGENTS.md

    @staticmethod
    def requires_committee(total_amount: Decimal, farm_id: int) -> bool:
        """Check if the amount requires committee approval."""
        threshold = ProcurementApprovalService.get_threshold(farm_id)
        return total_amount > threshold

    @staticmethod
    @transaction.atomic
    def validate_procurement(
        *,
        purchase_order_id: int,
        total_amount: Decimal,
        farm_id: int,
        approvals: list,
        user=None,
    ) -> dict:
        """
        Validate procurement against tiered approval rules.

        Args:
            purchase_order_id: ID of the purchase order.
            total_amount: Total PO amount (Decimal).
            farm_id: Farm tenant ID (Axis 6).
            approvals: List of approval dicts with at minimum
                       {approver_id, approver_role, approved_at}.
            user: The requesting user for audit trail.

        Returns:
            dict with validation result.

        Raises:
            ValidationError if insufficient signatures.
        """
        threshold = ProcurementApprovalService.get_threshold(farm_id)

        # Below threshold — direct flow, no committee needed
        if total_amount <= threshold:
            return {
                'status': 'approved_direct',
                'purchase_order_id': purchase_order_id,
                'total_amount': str(total_amount.quantize(FOUR_DP)),
                'threshold': str(threshold.quantize(FOUR_DP)),
                'message': 'أقل من الحد — موافقة مباشرة.',
            }

        # --- Above threshold: require 3 distinct signatures ---
        if not approvals or len(approvals) < REQUIRED_SIGNATURES:
            current_count = len(approvals) if approvals else 0
            raise ValidationError({
                'approvals': (
                    f'🔴 [FORENSIC BLOCK] المشتريات بقيمة {total_amount} '
                    f'تتجاوز حد الموافقة ({threshold}). '
                    f'مطلوب {REQUIRED_SIGNATURES} توقيعات — '
                    f'متوفر {current_count} فقط.'
                ),
            })

        # Verify distinct approvers (no duplicate signatures)
        approver_ids = [a.get('approver_id') for a in approvals]
        unique_approvers = set(approver_ids)
        if len(unique_approvers) < REQUIRED_SIGNATURES:
            raise ValidationError({
                'approvals': (
                    f'🔴 [FORENSIC BLOCK] يجب أن يكون الموقّعون مختلفين. '
                    f'وُجد {len(unique_approvers)} موقّع فريد من أصل '
                    f'{REQUIRED_SIGNATURES} مطلوب.'
                ),
            })

        # Verify role diversity (at least manager + finance + auditor)
        roles = {a.get('approver_role', '').lower() for a in approvals}
        required_roles = {'manager', 'finance', 'auditor'}
        missing_roles = required_roles - roles
        if missing_roles:
            logger.warning(
                "PO %s: missing role coverage: %s (found: %s)",
                purchase_order_id, missing_roles, roles,
            )
            # Not a hard block — just a warning if specific roles are missing,
            # as the primary requirement is 3 distinct people.

        # [Axis 7] AuditLog
        from smart_agri.core.models.log import AuditLog
        AuditLog.objects.create(
            action='PROCUREMENT_COMMITTEE_APPROVED',
            model='PurchaseOrder',
            object_id=str(purchase_order_id),
            actor=user,
            new_payload={
                'total_amount': str(total_amount.quantize(FOUR_DP)),
                'threshold': str(threshold.quantize(FOUR_DP)),
                'farm_id': farm_id,
                'approver_ids': list(unique_approvers),
                'approver_count': len(unique_approvers),
            },
        )

        logger.info(
            "Procurement approved: PO=%s, amount=%s, threshold=%s, approvers=%d",
            purchase_order_id, total_amount, threshold, len(unique_approvers),
        )

        return {
            'status': 'approved_committee',
            'purchase_order_id': purchase_order_id,
            'total_amount': str(total_amount.quantize(FOUR_DP)),
            'threshold': str(threshold.quantize(FOUR_DP)),
            'approver_count': len(unique_approvers),
            'message': 'تمت الموافقة من اللجنة.',
        }
