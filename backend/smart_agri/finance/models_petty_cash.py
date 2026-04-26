from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

from smart_agri.core.models.base import SoftDeleteModel

class PettyCashRequest(SoftDeleteModel):
    """
    طلب عهدة نقدية.
    """
    STATUS_PENDING = "PENDING"
    STATUS_APPROVED = "APPROVED"
    STATUS_DISBURSED = "DISBURSED"
    STATUS_SETTLED = "SETTLED"
    STATUS_CANCELLED = "CANCELLED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending Approval"),
        (STATUS_APPROVED, "Approved - Awaiting Disbursement"),
        (STATUS_DISBURSED, "Disbursed - Active Custody"),
        (STATUS_SETTLED, "Settled & Closed"),
        (STATUS_CANCELLED, "Cancelled/Rejected"),
    ]

    farm = models.ForeignKey("core.Farm", on_delete=models.CASCADE, related_name="petty_cash_requests")
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="requested_petty_cash")
    amount = models.DecimalField(max_digits=19, decimal_places=4)
    description = models.CharField(max_length=255)
    
    # Analytical Dimension (Optional)
    cost_center = models.ForeignKey(
        'finance.CostCenter', 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True,
        related_name='petty_cash_requests'
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_petty_cash")
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Treasury Linkage
    disbursed_transaction = models.ForeignKey(
        'finance.TreasuryTransaction', 
        null=True, blank=True, 
        on_delete=models.SET_NULL,
        related_name='petty_cash_disbursements'
    )
    
    class Meta:
        managed = True
        db_table = "finance_pettycashrequest"
        verbose_name = "طلب عهدة نقدية"
        verbose_name_plural = "طلبات العهد النقدية"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(check=models.Q(amount__gt=0), name="pettycash_amount_positive"),
        ]

    def clean(self):
        super().clean()
        if self.amount is not None and self.amount <= 0:
            raise ValidationError({"amount": "Petty Cash amount must be strictly greater than zero."})

    def __str__(self):
        return f"Petty Cash {self.pk} - {self.amount} - {self.get_status_display()}"


class PettyCashSettlement(SoftDeleteModel):
    """
    تسوية عهدة نقدية.
    """
    STATUS_PENDING = "PENDING"
    STATUS_APPROVED = "APPROVED"
    STATUS_REJECTED = "REJECTED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending Review"),
        (STATUS_APPROVED, "Approved & Posted"),
        (STATUS_REJECTED, "Rejected"),
    ]

    request = models.OneToOneField(PettyCashRequest, on_delete=models.CASCADE, related_name="settlement")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    
    # Financial fields computed from lines or input by requester
    total_expenses = models.DecimalField(max_digits=19, decimal_places=4, default=Decimal("0.0000"))
    refund_amount = models.DecimalField(max_digits=19, decimal_places=4, default=Decimal("0.0000"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    settled_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="settled_petty_cash")
    settled_at = models.DateTimeField(null=True, blank=True)
    approval_note = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "finance_pettycashsettlement"
        verbose_name = "تسوية عهدة"
        verbose_name_plural = "تسويات العهد"

    def clean(self):
        super().clean()
        if self.total_expenses < 0 or self.refund_amount < 0:
            raise ValidationError("Expenses and Refund amounts cannot be negative.")
        if self.request_id and (self.total_expenses + self.refund_amount > self.request.amount):
             raise ValidationError("Total expenses plus refund cannot exceed the originally requested amount.")


class PettyCashLine(SoftDeleteModel):
    """
    البنود الفعلية لتسوية العهدة (الفواتير المصروفة).
    """
    settlement = models.ForeignKey(PettyCashSettlement, on_delete=models.CASCADE, related_name="lines")
    amount = models.DecimalField(max_digits=19, decimal_places=4)
    description = models.CharField(max_length=255)
    date = models.DateField(default=timezone.now)
    
    budget_classification = models.ForeignKey(
        'finance.BudgetClassification',
        on_delete=models.PROTECT,
        related_name="petty_cash_expenses",
        null=True, blank=True
    )
    
    # Optionally link to a generated ActualExpense row after approval
    actual_expense = models.ForeignKey(
        'finance.ActualExpense',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="petty_cash_lines"
    )

    # [Axis 17] Financial Liability Bridge
    related_daily_log = models.ForeignKey(
        'core.DailyLog',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="petty_cash_settlements",
        help_text="ربط بند التسوية بيومية عمل لإغلاق التزامات الأجور"
    )
    is_labor_settlement = models.BooleanField(
        default=False,
        help_text="هل هذا البند مخصص لتسوية أجور عمالة تم إثباتها مسبقاً؟"
    )

    class Meta:
        managed = True
        db_table = "finance_pettycashline"
        verbose_name = "بند تسوية عهدة"
        verbose_name_plural = "بنود تسوية العهد"

    def clean(self):
        super().clean()
        if self.amount is not None and self.amount <= 0:
            raise ValidationError({"amount": "Expense amount must be strictly positive."})
            
        # [AGRI-GUARDIAN Phase 6] Petty Cash Overdraft Block
        if self.amount and self.settlement_id:
            existing_lines = self.settlement.lines.exclude(pk=self.pk) if self.pk else self.settlement.lines.all()
            current_total = sum(line.amount for line in existing_lines)
            
            if current_total + self.amount > self.settlement.request.amount:
                raise ValidationError({
                    "amount": f"🔴 [FORENSIC BLOCK] السحب المكشوف مرفوض. إجمالي الفواتير المضافة ({current_total + self.amount}) يتجاوز مبلغ العهدة الأصلية المستلمة ({self.settlement.request.amount})."
                })
