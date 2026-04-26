from typing import Iterable, Dict, Any
from django.db import transaction

from smart_agri.finance.models import FinancialLedger
from smart_agri.finance.services.core_finance import FinanceService


class FinancialImportService:
    """
    Service to import financial journals via the approved service layer.
    Prevents bypassing validation by avoiding bulk_create on sensitive tables.
    """

    @staticmethod
    @transaction.atomic
    def import_ledger_entries(entries: Iterable[Dict[str, Any]], user=None):
        """
        Each entry must include: farm, account_code, debit, credit, description, (optional) currency, activity.
        """
        for entry in entries:
            farm = entry["farm"]
            account_code = entry["account_code"]
            debit = entry.get("debit")
            credit = entry.get("credit")
            description = entry.get("description", "Imported entry")
            currency = entry.get("currency")
            activity = entry.get("activity")

            FinanceService.post_manual_ledger_entry(
                farm=farm,
                account_code=account_code,
                debit=debit,
                credit=credit,
                description=description,
                user=user,
                currency=currency,
                activity=activity,
            )

        return FinancialLedger.objects.filter(
            farm__in={entry["farm"] for entry in entries}
        )
