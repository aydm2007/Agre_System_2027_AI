from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from smart_agri.core.models.base import SoftDeleteModel


class CashBox(SoftDeleteModel):
    MASTER_SAFE = "MASTER_SAFE"
    SUB_SAFE = "SUB_SAFE"
    BANK_ACCOUNT = "BANK_ACCOUNT"

    BOX_TYPE_CHOICES = [
        (MASTER_SAFE, "Main Farm Safe"),
        (SUB_SAFE, "User Custody Safe"),
        (BANK_ACCOUNT, "Bank Account"),
    ]

    farm = models.ForeignKey("core.Farm", on_delete=models.PROTECT, related_name="cash_boxes")
    name = models.CharField(max_length=120)
    box_type = models.CharField(max_length=20, choices=BOX_TYPE_CHOICES, db_index=True)
    currency = models.CharField(max_length=10, default="YER")
    balance = models.DecimalField(max_digits=19, decimal_places=4, default=Decimal("0.0000"))

    class Meta:
        managed = True
        db_table = "core_cashbox"
        verbose_name = "صندوق النقد"
        verbose_name_plural = "صناديق النقد"
        constraints = [
            models.UniqueConstraint(
                fields=["farm", "name"],
                condition=models.Q(deleted_at__isnull=True),
                name="uq_cashbox_farm_name_active",
            ),
            models.CheckConstraint(check=models.Q(balance__gte=0), name="cashbox_balance_non_negative"),
        ]

    def __str__(self) -> str:
        return f"{self.farm_id}:{self.name}"


class TreasuryTransaction(SoftDeleteModel):
    """Append-only treasury journal.

    This is the ONLY supported way to mutate CashBox balances.
    """

    RECEIPT = "RECEIPT"
    PAYMENT = "PAYMENT"
    EXPENSE = "EXPENSE"
    REMITTANCE = "REMITTANCE"

    TRANSACTION_TYPE_CHOICES = [
        (RECEIPT, "Customer Receipt"),
        (PAYMENT, "Vendor Payment"),
        (EXPENSE, "Petty Cash Expense"),
        (REMITTANCE, "Remittance to Sector HQ"),
    ]

    OUTFLOW_TYPES = {PAYMENT, EXPENSE, REMITTANCE}

    farm = models.ForeignKey("core.Farm", on_delete=models.PROTECT, related_name="treasury_transactions")
    cash_box = models.ForeignKey(CashBox, on_delete=models.PROTECT, related_name="transactions")
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES, db_index=True)
    amount = models.DecimalField(max_digits=19, decimal_places=4)
    exchange_rate = models.DecimalField(max_digits=19, decimal_places=4, default=Decimal("1.0000"))
    reference = models.CharField(max_length=120, blank=True, null=True)
    note = models.TextField(blank=True, null=True)

    # Analytical Dimensions (Ultimate Edition)
    cost_center = models.ForeignKey(
        'finance.CostCenter', 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True,
        related_name='treasury_transactions',
        help_text="مركز التكلفة التحليلي (Dimension 1)"
    )
    analytical_tags = models.JSONField(
        default=dict, 
        blank=True, 
        help_text="وسوم تحليلية إضافية (مثل: دورة المحصول، المعدة، الخ)"
    )

    # Idempotency: MUST come from X-Idempotency-Key header.
    # Enforced to <= 80 chars to preserve collision-safety when propagating to ledger keys.
    idempotency_key = models.CharField(max_length=80, unique=True, db_index=True)

    # Who was paid / received (optional but strongly preferred)
    party_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        related_name="treasury_parties",
        null=True,
        blank=True,
    )
    party_object_id = models.CharField(max_length=36, null=True, blank=True)
    party = GenericForeignKey("party_content_type", "party_object_id")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="treasury_transactions_created",
        help_text="User who created the treasury transaction",
    )

    class Meta:
        managed = True
        db_table = "core_treasurytransaction"
        verbose_name = "حركة الخزينة"
        verbose_name_plural = "حركات الخزينة"
        ordering = ["-created_at"]
        permissions = (
            ("can_post_treasury", "يمكنه تدبير عمليات الخزينة والصناديق"),
        )
        constraints = [
            models.CheckConstraint(check=models.Q(amount__gt=0), name="treasury_amount_positive"),
            models.CheckConstraint(check=models.Q(exchange_rate__gt=0), name="treasury_exchange_rate_positive"),
        ]

    def clean(self):
        super().clean()

        # Enforce append-only at ORM layer.
        if not self._state.adding:
            raise ValidationError("TreasuryTransaction is append-only and cannot be edited.")

        if self.cash_box_id and self.farm_id and self.cash_box.farm_id != self.farm_id:
            raise ValidationError({"cash_box": "CashBox farm must match transaction farm."})

        if self.amount is not None and self.amount <= Decimal("0.0000"):
            raise ValidationError({"amount": "Transaction amount must be positive."})

        if self.exchange_rate is not None and self.exchange_rate <= Decimal("0.0000"):
            raise ValidationError({"exchange_rate": "Exchange rate must be positive."})

        if self.idempotency_key and len(self.idempotency_key) > 80:
            raise ValidationError({"idempotency_key": "Idempotency key must be <= 80 characters."})

    def save(self, *args, **kwargs):
        # All writes must be atomic and lock the CashBox row.
        with transaction.atomic():
            cash_box = CashBox.objects.select_for_update().get(pk=self.cash_box_id)

            if cash_box.deleted_at is not None or not cash_box.is_active:
                raise ValidationError({"cash_box": "CashBox is inactive or deleted."})

            if cash_box.farm_id != self.farm_id:
                raise ValidationError({"cash_box": "CashBox farm must match transaction farm."})

            self.full_clean()

            if self.transaction_type in self.OUTFLOW_TYPES:
                if cash_box.balance < self.amount:
                    raise ValidationError({"amount": "Insufficient cash box balance for outflow transaction."})
                cash_box.balance = cash_box.balance - self.amount
            else:
                cash_box.balance = cash_box.balance + self.amount

            cash_box.updated_at = timezone.now()
            cash_box.full_clean()
            cash_box.save(update_fields=["balance", "updated_at"])

            self.updated_at = timezone.now()
            result = super().save(*args, **kwargs)
            
            # [AGRI-GUARDIAN §Axis-7] Forensic audit trail for treasury mutations
            from smart_agri.core.services.sensitive_audit import log_sensitive_mutation
            log_sensitive_mutation(
                model_name="TreasuryTransaction",
                object_id=str(self.pk),
                action="CREATE",
                actor=self.created_by if hasattr(self, 'created_by') else None,
                old_value=None,
                new_value={
                    "amount": str(self.amount),
                    "transaction_type": self.transaction_type,
                    "cash_box": str(self.cash_box_id),
                    "reference": self.reference or "",
                },
                reason=f"Treasury {self.transaction_type}: {self.reference}"
            )
            return result
