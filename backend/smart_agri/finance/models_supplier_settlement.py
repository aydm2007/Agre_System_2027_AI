from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from smart_agri.core.models.base import SoftDeleteModel


class SupplierSettlement(SoftDeleteModel):
    STATUS_DRAFT = "DRAFT"
    STATUS_UNDER_REVIEW = "UNDER_REVIEW"
    STATUS_APPROVED = "APPROVED"
    STATUS_PARTIALLY_PAID = "PARTIALLY_PAID"
    STATUS_PAID = "PAID"
    STATUS_REJECTED = "REJECTED"
    STATUS_REOPENED = "REOPENED"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_UNDER_REVIEW, "Under Review"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_PARTIALLY_PAID, "Partially Paid"),
        (STATUS_PAID, "Paid"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_REOPENED, "Reopened"),
    ]

    PAYMENT_METHOD_CASH_BOX = "CASH_BOX"
    PAYMENT_METHOD_BANK = "BANK"
    PAYMENT_METHOD_CHOICES = [
        (PAYMENT_METHOD_CASH_BOX, "Cash Box"),
        (PAYMENT_METHOD_BANK, "Bank"),
    ]

    farm = models.ForeignKey(
        "core.Farm",
        on_delete=models.CASCADE,
        related_name="supplier_settlements",
    )
    purchase_order = models.OneToOneField(
        "inventory.PurchaseOrder",
        on_delete=models.PROTECT,
        related_name="supplier_settlement",
    )
    invoice_reference = models.CharField(max_length=120, blank=True, default="")
    due_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default=PAYMENT_METHOD_CASH_BOX,
    )
    payable_amount = models.DecimalField(max_digits=19, decimal_places=4)
    paid_amount = models.DecimalField(max_digits=19, decimal_places=4, default=Decimal("0.0000"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)
    cost_center = models.ForeignKey(
        "finance.CostCenter",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="supplier_settlements",
    )
    crop_plan = models.ForeignKey(
        "core.CropPlan",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="supplier_settlements",
    )
    latest_treasury_transaction = models.ForeignKey(
        "finance.TreasuryTransaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="latest_for_supplier_settlements",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="supplier_settlements_created",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supplier_settlements_reviewed",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supplier_settlements_approved",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_reason = models.TextField(blank=True, default="")

    class Meta:
        managed = True
        db_table = "finance_suppliersettlement"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(check=models.Q(payable_amount__gt=0), name="supplier_settlement_payable_positive"),
            models.CheckConstraint(check=models.Q(paid_amount__gte=0), name="supplier_settlement_paid_non_negative"),
        ]

    @property
    def vendor_name(self):
        return self.purchase_order.vendor_name

    @property
    def remaining_balance(self):
        remaining = (self.payable_amount or Decimal("0.0000")) - (self.paid_amount or Decimal("0.0000"))
        return remaining.quantize(Decimal("0.0001"))

    @property
    def reconciliation_state(self):
        if self.paid_amount == self.payable_amount:
            return "MATCHED"
        if self.paid_amount > Decimal("0.0000"):
            return "PARTIAL"
        return "OPEN"

    @property
    def variance_severity(self):
        today = timezone.localdate()
        if self.status == self.STATUS_REJECTED:
            return "critical"
        if self.due_date and today > self.due_date and self.remaining_balance > Decimal("0.0000"):
            return "warning"
        if self.status == self.STATUS_PARTIALLY_PAID:
            return "warning"
        return "normal"

    def clean(self):
        super().clean()
        if self.purchase_order_id and self.farm_id and self.purchase_order.farm_id != self.farm_id:
            raise ValidationError({"purchase_order": "Purchase order farm must match settlement farm."})
        if self.payable_amount is not None and self.payable_amount <= Decimal("0.0000"):
            raise ValidationError({"payable_amount": "Payable amount must be positive."})
        if self.paid_amount is not None and self.paid_amount < Decimal("0.0000"):
            raise ValidationError({"paid_amount": "Paid amount cannot be negative."})
        if self.paid_amount is not None and self.payable_amount is not None and self.paid_amount > self.payable_amount:
            raise ValidationError({"paid_amount": "Paid amount cannot exceed payable amount."})


class SupplierSettlementPayment(SoftDeleteModel):
    settlement = models.ForeignKey(
        "finance.SupplierSettlement",
        on_delete=models.CASCADE,
        related_name="payments",
    )
    treasury_transaction = models.ForeignKey(
        "finance.TreasuryTransaction",
        on_delete=models.PROTECT,
        related_name="supplier_settlement_payments",
    )
    amount = models.DecimalField(max_digits=19, decimal_places=4)
    note = models.CharField(max_length=255, blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="supplier_settlement_payments_created",
    )

    class Meta:
        managed = True
        db_table = "finance_suppliersettlementpayment"
        ordering = ["created_at"]
        constraints = [
            models.CheckConstraint(check=models.Q(amount__gt=0), name="supplier_settlement_payment_positive"),
        ]

    def clean(self):
        super().clean()
        if self.amount is not None and self.amount <= Decimal("0.0000"):
            raise ValidationError({"amount": "Payment amount must be positive."})
