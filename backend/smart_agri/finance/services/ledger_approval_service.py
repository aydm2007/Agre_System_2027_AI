from django.db import transaction

from smart_agri.finance.models import FinancialLedger


class LedgerApprovalService:
    """Governed maker-checker approval for pending manual ledger entries."""

    @staticmethod
    @transaction.atomic
    def approve_pending_entries(*, farm_id: int, entry_ids: list[int], approver) -> int:
        entries = FinancialLedger.objects.select_for_update().filter(
            id__in=entry_ids,
            is_posted=False,
            farm_id=farm_id,
        )
        approved_count = 0
        for entry in entries:
            entry.is_posted = True
            entry.approved_by = approver
            entry.save(update_fields=["is_posted", "approved_by"])
            approved_count += 1
        return approved_count
