from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from smart_agri.finance.models import FinancialLedger
from smart_agri.finance.models_treasury import CashBox, TreasuryTransaction


def _resolve_cashbox_account_code(cash_box: CashBox) -> str:
    if cash_box.box_type == CashBox.BANK_ACCOUNT:
        return FinancialLedger.ACCOUNT_BANK
    return FinancialLedger.ACCOUNT_CASH_ON_HAND


def _is_employee_party(tx: TreasuryTransaction) -> bool:
    return bool(tx.party_content_type_id) and tx.party_content_type.model == "employee"


def _is_vendor_party(tx: TreasuryTransaction) -> bool:
    return bool(tx.party_content_type_id) and tx.party_content_type.model == "vendor"


def _resolve_counterparty_account_code(tx: TreasuryTransaction) -> str:
    if tx.transaction_type == TreasuryTransaction.RECEIPT:
        return FinancialLedger.ACCOUNT_RECEIVABLE

    if tx.transaction_type == TreasuryTransaction.PAYMENT:
        if _is_employee_party(tx):
            return FinancialLedger.ACCOUNT_PAYABLE_SALARIES
        if _is_vendor_party(tx):
            return FinancialLedger.ACCOUNT_PAYABLE_VENDOR
        return FinancialLedger.ACCOUNT_PAYABLE_VENDOR

    if tx.transaction_type == TreasuryTransaction.REMITTANCE:
        return FinancialLedger.ACCOUNT_SECTOR_PAYABLE

    # EXPENSE
    return FinancialLedger.ACCOUNT_EXPENSE_ADMIN


def _build_narrative(tx: TreasuryTransaction) -> str:
    note = (tx.note or "").strip()
    reference = tx.reference or "N/A"

    if tx.transaction_type == TreasuryTransaction.RECEIPT:
        base = f"Receipt #{reference}"
    elif tx.transaction_type == TreasuryTransaction.PAYMENT:
        base = f"Payment #{reference}"
    elif tx.transaction_type == TreasuryTransaction.REMITTANCE:
        base = f"Remittance #{reference}"
    else:
        base = f"Expense #{reference}"

    return f"{base}: {note}" if note else base


@receiver(post_save, sender=TreasuryTransaction)
def post_treasury_transaction_to_ledger(sender, instance: TreasuryTransaction, created: bool, **kwargs):
    if not created:
        return

    with transaction.atomic():
        content_type = ContentType.objects.get_for_model(TreasuryTransaction)
        description = _build_narrative(instance)
        amount = Decimal(instance.amount)
        exchange_rate = Decimal(instance.exchange_rate)

        cash_account = _resolve_cashbox_account_code(instance.cash_box)
        counterparty_account = _resolve_counterparty_account_code(instance)

        if instance.transaction_type == TreasuryTransaction.RECEIPT:
            debit_account = cash_account
            credit_account = counterparty_account
        else:
            debit_account = counterparty_account
            credit_account = cash_account

        common = {
            "content_type": content_type,
            "object_id": str(instance.pk),
            "farm_id": instance.farm_id,
            "description": description,
            "currency": instance.cash_box.currency,
            "exchange_rate_at_moment": exchange_rate,
            "entity_content_type": instance.party_content_type,
            "entity_object_id": instance.party_object_id,
            "created_by": instance.created_by,
        }

        # Propagate idempotency into ledger lines.
        base_key = f"LGR:{instance.idempotency_key}"

        FinancialLedger.objects.create(
            **common,
            account_code=debit_account,
            debit=amount,
            credit=Decimal("0.0000"),
            idempotency_key=f"{base_key}:D",
        )

        FinancialLedger.objects.create(
            **common,
            account_code=credit_account,
            debit=Decimal("0.0000"),
            credit=amount,
            idempotency_key=f"{base_key}:C",
        )
