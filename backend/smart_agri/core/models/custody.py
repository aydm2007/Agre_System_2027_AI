from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from .base import SoftDeleteModel
from .farm import Farm, Location
from .settings import Supervisor
from smart_agri.inventory.models import Item


class CustodyTransfer(SoftDeleteModel):
    STATUS_DRAFT = "draft"
    STATUS_ISSUED_PENDING_ACCEPTANCE = "issued_pending_acceptance"
    STATUS_ACCEPTED = "accepted"
    STATUS_PARTIALLY_CONSUMED = "partially_consumed"
    STATUS_RETURNED = "returned"
    STATUS_RECONCILED = "reconciled"
    STATUS_REJECTED = "rejected"
    STATUS_EXPIRED_REVIEW = "expired_review"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "مسودة"),
        (STATUS_ISSUED_PENDING_ACCEPTANCE, "صادرة بانتظار القبول"),
        (STATUS_ACCEPTED, "تم قبول العهدة"),
        (STATUS_PARTIALLY_CONSUMED, "مستهلكة جزئياً"),
        (STATUS_RETURNED, "مرتجعة"),
        (STATUS_RECONCILED, "مصفاة"),
        (STATUS_REJECTED, "مرفوضة"),
        (STATUS_EXPIRED_REVIEW, "منتهية وتحتاج مراجعة"),
    ]

    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="custody_transfers")
    supervisor = models.ForeignKey(
        Supervisor, on_delete=models.PROTECT, related_name="custody_transfers"
    )
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="custody_transfers")
    source_location = models.ForeignKey(
        Location, on_delete=models.PROTECT, related_name="custody_transfers_out"
    )
    in_transit_location = models.ForeignKey(
        Location, on_delete=models.PROTECT, related_name="custody_transfers_transit"
    )
    custody_location = models.ForeignKey(
        Location, on_delete=models.PROTECT, related_name="custody_transfers_custody"
    )
    batch_number = models.CharField(max_length=100, blank=True, default="")
    status = models.CharField(
        max_length=40, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True
    )
    issued_qty = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal("0.000"))
    accepted_qty = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal("0.000"))
    returned_qty = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal("0.000"))
    note = models.CharField(max_length=255, blank=True, default="")
    idempotency_key = models.CharField(max_length=128, blank=True, default="", db_index=True)
    issued_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    reconciled_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="custody_transfers_issued",
    )
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="custody_transfers_accepted",
    )
    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="custody_transfers_rejected",
    )
    reconciled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="custody_transfers_reconciled",
    )

    class Meta:
        db_table = "core_custody_transfer"
        verbose_name = "تحويل عهدة مواد"
        verbose_name_plural = "تحويلات عهدة المواد"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["farm", "supervisor", "status"], name="custody_transfer_farm_sup_idx"),
            models.Index(fields=["farm", "item", "status"], name="custody_transfer_farm_item_idx"),
        ]
        constraints = [
            models.CheckConstraint(check=Q(issued_qty__gt=0), name="custody_transfer_issued_qty_gt_zero"),
            models.CheckConstraint(check=Q(accepted_qty__gte=0), name="custody_transfer_accepted_qty_non_negative"),
            models.CheckConstraint(check=Q(returned_qty__gte=0), name="custody_transfer_returned_qty_non_negative"),
        ]

    @property
    def outstanding_qty(self) -> Decimal:
        return (self.accepted_qty - self.returned_qty).quantize(Decimal("0.001"))

    def clean(self):
        super().clean()
        if self.farm_id and self.supervisor_id and self.supervisor.farm_id != self.farm_id:
            raise ValidationError({"supervisor": "المشرف لا يتبع نفس المزرعة."})
        for field_name in ("source_location", "in_transit_location", "custody_location"):
            location = getattr(self, field_name, None)
            if location and location.farm_id != self.farm_id:
                raise ValidationError({field_name: "الموقع لا يتبع نفس المزرعة."})
        if self.accepted_qty > self.issued_qty:
            raise ValidationError({"accepted_qty": "لا يمكن أن تتجاوز الكمية المقبولة الكمية الصادرة."})
        if self.returned_qty > self.accepted_qty:
            raise ValidationError({"returned_qty": "لا يمكن أن تتجاوز الكمية المرتجعة الكمية المقبولة."})

    def mark_expired_review(self):
        self.status = self.STATUS_EXPIRED_REVIEW
        self.reconciled_at = timezone.now()

