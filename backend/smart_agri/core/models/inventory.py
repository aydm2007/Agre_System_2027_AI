from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, F
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.db import transaction

from smart_agri.core.models.base import SoftDeleteModel
from smart_agri.core.models.farm import Farm, Location
# from .settings import Uom
from smart_agri.inventory.models import Unit, UnitConversion, Item, ItemInventory, StockMovement

"""
[ZOMBIE CODE REMOVED]
The classes Unit, UnitConversion, Item, ItemInventory, ItemInventoryBatch, StockMovement
are imported from smart_agri.inventory.models and should NOT be redefined here.
"""


class HarvestLot(SoftDeleteModel):
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="harvest_lots")
    # Using string reference for Crop to avoid circular dependency if Crop also imports inventory
    crop = models.ForeignKey("Crop", on_delete=models.CASCADE, related_name="harvest_lots")
    crop_plan = models.ForeignKey(
        "CropPlan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="harvest_lots",
    )
    product = models.ForeignKey(
        'CropProduct',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="harvest_lots",
    )
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name="harvest_lots")
    harvest_date = models.DateField()
    grade = models.CharField(max_length=50, blank=True, default="First")
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit = models.ForeignKey(
        Unit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="harvest_lots",
    )
    uom = models.CharField(max_length=40, default="kg")
    
    # [V21 Forensic Alignment]
    status = models.CharField(max_length=20, default="draft", verbose_name="حالة الدفعة")
    is_final = models.BooleanField(default=False, verbose_name="نهائي")
    eternity_proof_id = models.UUIDField(null=True, blank=True, help_text="Sovereign forensic hash bundle")

    class Meta:
        verbose_name = "دفعة حصاد"
        verbose_name_plural = "دفعات الحصاد"
        constraints = [
            models.CheckConstraint(check=Q(quantity__gt=0), name="harvestlot_quantity_positive")
        ]


class BiologicalAssetCohort(SoftDeleteModel):
    """
    [AGRI-GUARDIAN] Axis 11 Compliance: Biological Asset Hierarchy
    Tracks perennial trees chronologically by planting batches.
    A single location can have multiple cohorts of the same variety with different ages.
    """
    STATUS_JUVENILE = 'JUVENILE'
    STATUS_PRODUCTIVE = 'PRODUCTIVE'
    STATUS_SICK = 'SICK'
    STATUS_EXCLUDED = 'EXCLUDED'
    STATUS_RENEWING = 'RENEWING'

    STATUS_CHOICES = [
        (STATUS_JUVENILE, 'Juvenile (Non-Productive)'),
        (STATUS_PRODUCTIVE, 'Productive'),
        (STATUS_SICK, 'Sick / Treatment'),
        (STATUS_EXCLUDED, 'Excluded / Dead'),
        (STATUS_RENEWING, 'Renewing (Ratooning)'),
    ]

    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="asset_cohorts")
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="asset_cohorts")
    crop = models.ForeignKey('Crop', on_delete=models.CASCADE, related_name="asset_cohorts")
    variety = models.ForeignKey('CropVariety', on_delete=models.SET_NULL, null=True, blank=True, related_name="asset_cohorts")
    parent_cohort = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name="ratoons", help_text="Ratooning connection for crops like Banana")
    
    batch_name = models.CharField(max_length=200, help_text="e.g., Spring Planting 2024")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_JUVENILE)
    quantity = models.PositiveIntegerField(default=0)
    planted_date = models.DateField(help_text="Chronological origin of this batch to track maturity")

    # [Axis 11] Amortization fields for PRODUCTIVE cohorts
    capitalized_cost = models.DecimalField(
        max_digits=19, decimal_places=4, default=0,
        help_text="Total capitalized WIP at JUVENILE→PRODUCTIVE transition"
    )
    useful_life_years = models.PositiveIntegerField(
        default=25,
        help_text="Expected useful life in years for amortization calculation"
    )
    accumulated_depreciation = models.DecimalField(
        max_digits=19, decimal_places=4, default=0,
        help_text="Total accumulated depreciation posted to date (updated monthly by amortization task)"
    )
    default_planting_cost = models.DecimalField(
        max_digits=19, decimal_places=4, default=0,
        help_text="Fallback planting cost per unit when capitalized_cost is zero (configurable per cohort)"
    )

    class Meta:
        verbose_name = "Biological Asset Cohort"
        verbose_name_plural = "Biological Asset Cohorts"
        indexes = [
            models.Index(fields=["farm", "location", "crop", "variety"]),
            models.Index(fields=["status"]),
            models.Index(fields=["planted_date"]),
        ]

    def __str__(self):
        v_name = self.variety.name if self.variety else self.crop.name
        return f"{v_name} - {self.location.name} [{self.batch_name}] ({self.status}: {self.quantity})"


class TreeCensusVarianceAlert(models.Model):
    """
    [AGRI-GUARDIAN] Axis 11 Compliance: Loss Reconciliation Loop
    When a Daily Log detects missing trees, it creates this alert to trigger 
    an official Biological Asset Transaction instead of silently hacking the numbers.
    """
    STATUS_PENDING = 'PENDING'
    STATUS_RESOLVED = 'RESOLVED'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending Management Review'),
        (STATUS_RESOLVED, 'Resolved / Authorized'),
    ]

    log = models.ForeignKey('core.DailyLog', on_delete=models.CASCADE, null=True, blank=True, related_name="tree_census_alerts")
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="tree_census_alerts")
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="tree_census_alerts")
    crop = models.ForeignKey('Crop', on_delete=models.CASCADE, related_name="tree_census_alerts")
    cohort = models.ForeignKey(BiologicalAssetCohort, on_delete=models.SET_NULL, null=True, blank=True, related_name="variance_alerts", help_text="Linked cohort batch — set during resolution to target specific deduction")
    missing_quantity = models.PositiveIntegerField()
    reason = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        verbose_name = "Tree Census Variance Alert"
        verbose_name_plural = "Tree Census Variance Alerts"
        indexes = [
            models.Index(fields=["farm", "status"]),
        ]

    def __str__(self):
        return f"[{self.status}] Missing {self.missing_quantity} at {self.location.name}"


class BiologicalAssetTransaction(SoftDeleteModel):
    """
    [AGRI-GUARDIAN] Axis 11 Compliance: Capital Event Ledger
    Append-only ledger to track state transitions of tree cohorts without deleting or modifying history.
    """
    cohort = models.ForeignKey(BiologicalAssetCohort, on_delete=models.CASCADE, related_name="transactions")
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="asset_transactions")
    
    from_status = models.CharField(max_length=20, choices=BiologicalAssetCohort.STATUS_CHOICES, blank=True, null=True)
    to_status = models.CharField(max_length=20, choices=BiologicalAssetCohort.STATUS_CHOICES)
    quantity = models.PositiveIntegerField()
    
    transaction_date = models.DateField(auto_now_add=True)
    notes = models.TextField(blank=True, default="")
    reference_id = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = "Biological Asset Transaction"
        verbose_name_plural = "Biological Asset Transactions"
        ordering = ["-transaction_date", "-created_at"]

    def __str__(self):
        return f"{self.cohort.batch_name}: {self.quantity} -> {self.to_status}"


@receiver(post_save, sender=BiologicalAssetCohort)
def sync_location_tree_stock_for_cohort(sender, instance, created, **kwargs):
    """
    [Domain Event Handler]: Ensure a functional LocationTreeStock node exists 
    whenever an active cohort is maintained. This avoids strict filters breaking
    Daily Log operation dropdowns without forcing dirty Read-Model Fusions in the API.
    """
    if getattr(instance, 'deleted_at', None) is not None:
        return
        
    # Only active statuses require an operational stock node to exist (even if its count is 0)
    if instance.status not in [
        BiologicalAssetCohort.STATUS_JUVENILE,
        BiologicalAssetCohort.STATUS_PRODUCTIVE,
        BiologicalAssetCohort.STATUS_SICK,
        BiologicalAssetCohort.STATUS_RENEWING,
    ]:
        return
        
    if not instance.variety:
        return

    from smart_agri.core.models.tree import LocationTreeStock
    
    # Ensure the operational stock row exists for the daily log to select.
    # It does not forcefully overwrite current_tree_count to preserve variance/reconciliation integrity.
    stock, created_stock = LocationTreeStock.objects.get_or_create(
        location=instance.location,
        crop_variety=instance.variety,
        defaults={
            'current_tree_count': 0,
        }
    )
    if not created_stock and stock.deleted_at is not None:
        stock.deleted_at = None
        stock.save(update_fields=['deleted_at'])
