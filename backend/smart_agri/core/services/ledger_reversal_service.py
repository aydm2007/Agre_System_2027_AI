"""
Ledger Reversal Transaction Service - Protocol XV Compliance.

AGRI-GUARDIAN: Helper functions for creating reversal entries
when corrections are needed for immutable ledger records.

Financial Ledger rows are IMMUTABLE by database trigger.
This service provides the ONLY approved way to correct errors:
creating reversal (contra) entries.
"""
import hashlib
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


def generate_row_hash(
    account_code: str,
    debit: Decimal,
    credit: Decimal,
    description: str,
    created_at: datetime,
) -> str:
    """
    Generate a deterministic hash with Normalized Decimals.
    """
    # [Agri-Guardian] Force 2 decimal places string format to match DB standard (numeric(12,2))
    # This prevents hash mismatch between "100" and "100.00"
    fmt_debit = f"{debit:.2f}"
    fmt_credit = f"{credit:.2f}"
    
    # Use ISO format for date to ensure timezone consistencies don't break hash
    fmt_date = created_at.isoformat()

    data = f"{account_code}|{fmt_debit}|{fmt_credit}|{description}|{fmt_date}"
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def verify_row_hash(ledger_entry) -> bool:
    """
    Verify that a ledger entry's hash matches its content.
    Returns True if valid, False if tampered.
    """
    expected_hash = generate_row_hash(
        account_code=ledger_entry.account_code,
        debit=ledger_entry.debit,
        credit=ledger_entry.credit,
        description=ledger_entry.description,
        created_at=ledger_entry.created_at,
    )
    return ledger_entry.row_hash == expected_hash


def create_reversal_entry(
    original_entry_id: uuid.UUID,
    reason: str,
    user_id: int,
    approved_by_id: Optional[int] = None,
) -> "FinancialLedger":
    """
    Create a reversal entry for an immutable ledger record.
    
    This is the ONLY approved method to "undo" a ledger entry.
    The reversal swaps debit and credit amounts and references
    the original entry in the description.
    
    Args:
        original_entry_id: UUID of the entry to reverse
        reason: Explanation for the reversal (required for audit)
        user_id: ID of the user creating the reversal
        approved_by_id: Optional approver ID for dual approval
    
    Returns:
        The new reversal FinancialLedger entry
    
    Raises:
        ValueError: If original entry not found
        ValidationError: If reason is empty
    """
    from smart_agri.finance.models import FinancialLedger
    from django.core.exceptions import ValidationError
    
    if not reason or len(reason.strip()) < 10:
        raise ValidationError(
            "الإلغاء يتطلب سبباً واضحاً (10 أحرف على الأقل). "
            "Reversal requires a clear reason (minimum 10 characters)."
        )
    
    try:
        original = FinancialLedger.objects.get(pk=original_entry_id)
    except FinancialLedger.DoesNotExist:
        raise ValueError(f"القيد الأصلي غير موجود: {original_entry_id}")
    
    # Create reversal description with full audit trail
    reversal_description = (
        f"[إلغاء/REVERSAL] {reason} | "
        f"إلغاء للقيد الأصلي: {original_entry_id} | "
        f"Original: {original.description}"
    )
    
    with transaction.atomic():
        # Swap debit and credit to reverse the effect
        reversal = FinancialLedger(
            id=uuid.uuid4(),
            activity_id=original.activity_id,
            crop_plan_id=original.crop_plan_id,
            account_code=original.account_code,
            debit=original.credit,  # Swapped
            credit=original.debit,   # Swapped
            description=reversal_description[:255],  # Truncate if needed
            currency=original.currency,
            tax_amount=Decimal("0"),  # Reversals don't add new tax
            created_at=timezone.now(),
            created_by_id=user_id,
            approved_by_id=approved_by_id,
            content_type_id=original.content_type_id,
            object_id=original.object_id,
        )
        
        # Generate integrity hash
        reversal.row_hash = generate_row_hash(
            account_code=reversal.account_code,
            debit=reversal.debit,
            credit=reversal.credit,
            description=reversal.description,
            created_at=reversal.created_at,
        )
        
        reversal.save()
        
        logger.info(
            f"LEDGER_REVERSAL: Created reversal {reversal.id} for original {original_entry_id} "
            f"by user {user_id}. Reason: {reason[:50]}..."
        )
    
    return reversal


def verify_ledger_integrity(farm_id: Optional[int] = None) -> dict:
    """
    Comprehensive ledger integrity verification.
    
    Checks:
    1. All row hashes match content
    2. Debits equal credits
    3. No orphan references
    
    Returns a detailed report.
    """
    from smart_agri.finance.models import FinancialLedger
    from django.db.models import Sum
    
    filters = {}
    if farm_id:
        filters['activity__log__farm_id'] = farm_id
    
    entries = FinancialLedger.objects.filter(**filters)
    
    # Check 1: Row hash integrity
    tampered_entries = []
    for entry in entries.iterator():
        if not verify_row_hash(entry):
            tampered_entries.append(str(entry.id))
    
    # Check 2: Balance verification
    totals = entries.aggregate(
        total_debit=Sum('debit'),
        total_credit=Sum('credit')
    )
    total_debit = totals['total_debit'] or Decimal("0")
    total_credit = totals['total_credit'] or Decimal("0")
    difference = total_debit - total_credit
    is_balanced = difference == Decimal("0")
    
    # Check 3: Orphan references
    orphan_activities = entries.filter(
        activity_id__isnull=False
    ).exclude(
        activity__isnull=False
    ).count()
    
    return {
        "total_entries": entries.count(),
        "hash_verification": {
            "passed": len(tampered_entries) == 0,
            "tampered_count": len(tampered_entries),
            "tampered_ids": tampered_entries[:10],  # First 10 only
        },
        "balance_verification": {
            "is_balanced": is_balanced,
            "total_debit": str(total_debit),
            "total_credit": str(total_credit),
            "difference": str(difference),
        },
        "orphan_references": orphan_activities,
        "overall_status": (
            "✅ PASSING" 
            if is_balanced and len(tampered_entries) == 0 and orphan_activities == 0
            else "⚠️ ISSUES DETECTED"
        )
    }
