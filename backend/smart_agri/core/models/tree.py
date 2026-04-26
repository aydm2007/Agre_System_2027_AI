from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from .base import SoftDeleteModel
from .farm import Farm, Location
from .crop import CropVariety
from .activity import Activity

class TreeProductivityStatus(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name_en = models.CharField(max_length=120)
    name_ar = models.CharField(max_length=120)
    description = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Tree Productivity Status"
        verbose_name_plural = "Tree Productivity Statuses"

    def __str__(self):
        return f"{self.code} - {self.name_en}"

class TreeLossReason(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name_en = models.CharField(max_length=120)
    name_ar = models.CharField(max_length=120)
    description = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Tree Loss Reason"
        verbose_name_plural = "Tree Loss Reasons"

    def __str__(self):
        return f"{self.code} - {self.name_en}"

class LocationTreeStock(SoftDeleteModel):
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="tree_stocks")
    crop_variety = models.ForeignKey(CropVariety, on_delete=models.CASCADE, related_name="location_stocks")
    current_tree_count = models.IntegerField(default=0)
    productivity_status = models.ForeignKey(
        TreeProductivityStatus,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="location_stocks",
    )
    planting_date = models.DateField(null=True, blank=True)
    source = models.CharField(max_length=120, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # [Agri-Guardian: Strict Forensic Standard]
            # Enforce non-negative stock at the Database Level
            models.CheckConstraint(
                check=models.Q(current_tree_count__gte=0),
                name='check_stock_positive'
            ),
            # Ensure unique stock entry per location/crop pair to prevent Zombie duplicates
            models.UniqueConstraint(
                fields=["location", "crop_variety"],
                name='unique_location_crop_stock'
            )
        ]
        indexes = [
            models.Index(fields=["location"]),
            # models.Index(fields=["location", "crop_variety"]), # Redundant with UniqueConstraint
            models.Index(fields=["productivity_status"]),
        ]

    def __str__(self):
        return f"{self.location} - {self.crop_variety} ({self.current_tree_count})"



class TreeStockEvent(models.Model):
    PLANTING = "planting"
    LOSS = "loss"
    ADJUSTMENT = "adjustment"
    TRANSFER = "transfer"
    HARVEST = "harvest"
    INSPECTION = "inspection"
    EVENT_CHOICES = [
        (PLANTING, "Planting"),
        (LOSS, "Loss"),
        (ADJUSTMENT, "Adjustment"),
        (TRANSFER, "Transfer"),
        (HARVEST, "Harvest"),
        (INSPECTION, "Inspection"),
    ]

    location_tree_stock = models.ForeignKey(
        LocationTreeStock, on_delete=models.CASCADE, related_name="events"
    )
    activity = models.ForeignKey(
        Activity, null=True, blank=True, on_delete=models.SET_NULL, related_name="tree_events"
    )
    event_type = models.CharField(max_length=30, choices=EVENT_CHOICES)
    event_timestamp = models.DateTimeField(auto_now_add=True)
    tree_count_delta = models.IntegerField()
    resulting_tree_count = models.IntegerField(null=True, blank=True)
    loss_reason = models.ForeignKey(
        TreeLossReason, null=True, blank=True, on_delete=models.SET_NULL, related_name="events"
    )
    planting_date = models.DateField(null=True, blank=True)
    source = models.CharField(max_length=120, blank=True, default="")
    harvest_quantity = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    harvest_uom = models.CharField(max_length=40, null=True, blank=True)
    water_volume = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    water_uom = models.CharField(max_length=40, null=True, blank=True)
    fertilizer_quantity = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    fertilizer_uom = models.CharField(max_length=40, null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    # [AGRI-GUARDIAN Axis 2] Idempotency guard for offline sync retries
    idempotency_key = models.CharField(
        max_length=128, blank=True, default="", db_index=True,
        help_text="UUID for dedup on offline sync",
    )

    class Meta:
        indexes = [
            models.Index(fields=["location_tree_stock"]),
            models.Index(fields=["event_type"]),
            models.Index(fields=["loss_reason"]),
            models.Index(fields=["event_timestamp"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["idempotency_key"],
                condition=~models.Q(idempotency_key=""),
                name="unique_tree_stock_event_idempotency",
            ),
        ]

    def __str__(self):
        return f"{self.event_type} ({self.tree_count_delta}) - {self.location_tree_stock}"

class TreeServiceCoverage(SoftDeleteModel):
    GENERAL = 'general'
    FERTILIZATION = 'fertilization'
    IRRIGATION = 'irrigation'
    PEST_CONTROL = 'pest_control'
    PRUNING = 'pruning'
    HARVESTING = 'harvesting'
    SERVICE_TYPE_CHOICES = [
        (GENERAL, 'General Care'),
        (FERTILIZATION, 'Fertilization'),
        (IRRIGATION, 'Irrigation'),
        (PEST_CONTROL, 'Pest Control'),
        (PRUNING, 'Pruning'),
        (HARVESTING, 'Harvesting'),
    ]
    SCOPE_FARM = 'farm'
    SCOPE_LOCATION = 'location'
    SCOPE_TREE = 'tree'
    DISTRIBUTION_UNIFORM = "uniform"
    DISTRIBUTION_EXCEPTION_WEIGHTED = "exception_weighted"
    SERVICE_SCOPE_CHOICES = [
        (GENERAL, 'General'),
        (IRRIGATION, 'Irrigation'),
        (FERTILIZATION, 'Fertilization'),
        (PRUNING, 'Pruning'),
        (PEST_CONTROL, 'Pest Control'),
        (HARVESTING, 'Harvesting'),
        (SCOPE_FARM, 'Entire Farm'),
        (SCOPE_LOCATION, 'Specific Location'),
        (SCOPE_TREE, 'Specific Trees'),
    ]
    DISTRIBUTION_MODE_CHOICES = [
        (DISTRIBUTION_UNIFORM, "Uniform"),
        (DISTRIBUTION_EXCEPTION_WEIGHTED, "Exception Weighted"),
    ]

    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='service_coverages', null=True, blank=True, db_index=False)
    activity = models.ForeignKey(
        Activity, on_delete=models.CASCADE, related_name='service_coverages', null=True, blank=True
    )
    service_type = models.CharField(max_length=50, choices=SERVICE_TYPE_CHOICES, default=GENERAL)
    target_scope = models.CharField(max_length=20, choices=SERVICE_SCOPE_CHOICES, default=SCOPE_LOCATION)
    
    location = models.ForeignKey(
        Location, on_delete=models.SET_NULL, null=True, blank=True, related_name='covered_services'
    )
    crop_variety = models.ForeignKey(
        CropVariety, on_delete=models.SET_NULL, null=True, blank=True
    )
    trees_covered = models.IntegerField(default=0, help_text="Number of trees actually treated")
    area_covered_ha = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    cost_per_tree = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    distribution_mode = models.CharField(
        max_length=32,
        choices=DISTRIBUTION_MODE_CHOICES,
        default=DISTRIBUTION_UNIFORM,
    )
    distribution_factor = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    
    date = models.DateField(db_index=True, null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    
    # DB alignment and legacy support
    total_before = models.IntegerField(null=True, blank=True)
    total_after = models.IntegerField(null=True, blank=True)

    @property
    def service_count(self):
        return self.trees_covered

    @service_count.setter
    def service_count(self, value):
        self.trees_covered = value

    @property
    def service_scope(self):
        return self.target_scope

    @service_scope.setter
    def service_scope(self, value):
        self.target_scope = value
    
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_coverages"
    )

    class Meta:
        managed = True
        db_table = 'core_treeservicecoverage'
        verbose_name = "Tree Service Coverage"
        verbose_name_plural = "Tree Service Coverages"
        indexes = [
            # models.Index(fields=['farm', 'date']),
            models.Index(fields=['service_type']),
            models.Index(fields=['location']),
        ]

    def __str__(self):
        return f"{self.get_service_type_display()} - {self.date} ({self.trees_covered} trees)"

    def clean(self):
        super().clean()
        if self.trees_covered is not None and self.trees_covered < 0:
            raise ValidationError({"trees_covered": "عدد الأشجار المخدومة لا يمكن أن يكون سالباً."})
        if self.distribution_factor is not None and self.distribution_factor < 0:
            raise ValidationError({"distribution_factor": "معامل التوزيع لا يمكن أن يكون سالباً."})
        if self.location_id and self.crop_variety_id and self.trees_covered is not None:
            from .inventory import BiologicalAssetCohort
            stock = LocationTreeStock.objects.filter(
                location_id=self.location_id,
                crop_variety_id=self.crop_variety_id,
                deleted_at__isnull=True,
            ).first()
            available_capacity = int(getattr(stock, "current_tree_count", 0) or 0)
            if available_capacity <= 0:
                cohort_quantities = BiologicalAssetCohort.objects.filter(
                    deleted_at__isnull=True,
                    farm_id=self.farm_id,
                    location_id=self.location_id,
                    variety_id=self.crop_variety_id,
                    status__in=[
                        BiologicalAssetCohort.STATUS_JUVENILE,
                        BiologicalAssetCohort.STATUS_PRODUCTIVE,
                        BiologicalAssetCohort.STATUS_SICK,
                        BiologicalAssetCohort.STATUS_RENEWING,
                    ],
                ).values_list("quantity", flat=True)
                available_capacity = sum(int(quantity or 0) for quantity in cohort_quantities)
            positive_activity_delta = int(getattr(getattr(self, "activity", None), "tree_count_delta", 0) or 0) > 0
            if not positive_activity_delta and self.trees_covered > available_capacity:
                raise ValidationError({"trees_covered": "عدد الأشجار المخدومة يتجاوز رصيد الأشجار بالموقع."})

    def save(self, *args, **kwargs):
        valid_scopes = {choice[0] for choice in self.SERVICE_SCOPE_CHOICES}
        valid_types = {choice[0] for choice in self.SERVICE_TYPE_CHOICES}
        if self.target_scope not in valid_scopes:
            self.target_scope = self.GENERAL
        if self.service_type not in valid_types:
            self.service_type = self.GENERAL
        self.full_clean()
        return super().save(*args, **kwargs)


class BiologicalAssetImpairment(SoftDeleteModel):
    """
    Axis 18: Mass Casualty Write-off Workflow (IAS 41)
    
    Used to record extraordinary agricultural disasters (Frost, Disease, Fire)
    resulting in mass tree death. This strictly bypasses the standard Daily Log 
    shrinkage and mandates direct Financial Ledger impairment recognition.
    """

    farm = models.ForeignKey(
        'core.Farm',
        on_delete=models.CASCADE,
        related_name='asset_impairments',
        help_text="المزرعة لضمان عزل البيانات (Tenant Isolation)"
    )
    
    # Context
    location_tree_stock = models.ForeignKey(
        LocationTreeStock,
        on_delete=models.PROTECT,
        related_name='impairments',
        help_text="الأصل البيولوجي (الأشجار) المتأثر"
    )
    loss_reason = models.ForeignKey(
        TreeLossReason,
        on_delete=models.PROTECT,
        help_text="سبب الكارثة الجماعية (مبرر الانخفاض)"
    )
    
    # Metrics
    incident_date = models.DateField(db_index=True)
    dead_tree_count = models.PositiveIntegerField(
        help_text="عدد الأشجار النافقة (الخسارة المادية)"
    )
    impairment_value = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        help_text="القيمة المالية للخسارة المحكومة بمعيار IAS 41 (صافي القيمة الدفترية للأشجار الهالكة)"
    )
    
    # Traceability & Approval
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reported_impairments',
        help_text="المهندس المُبلغ عن الكارثة"
    )
    authorized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='authorized_impairments',
        help_text="توقيع الإدارة العليا الإلزامي للاعتماد המالي",
        null=True, blank=True
    )
    is_posted = models.BooleanField(
        default=False,
        help_text="تم ترحيل قيد الخسارة إلى الدفتر المالي (Financial Ledger)"
    )
    idempotency_key = models.CharField(
        max_length=255,
        unique=True,
        help_text="مفتاح الحماية ضد تكرار إعدام الكوارث"
    )
    notes = models.TextField(blank=True, default='')

    class Meta:
        managed = True
        db_table = 'core_biologicalasset_impairment'
        verbose_name = "إعدام جماعي (خسارة أصول)"
        verbose_name_plural = "سجلات الإعدام الجماعي للأصول"
        indexes = [
            models.Index(fields=['farm', 'incident_date']),
            models.Index(fields=['is_posted']),
        ]

    def __str__(self):
        return f"Impairment #{self.pk} - {self.location_tree_stock.crop_variety} (-{self.dead_tree_count} Trees)"

    def clean(self):
        super().clean()

        if not self.idempotency_key or not str(self.idempotency_key).strip():
            raise ValidationError({"idempotency_key": "Idempotency key is required for impairment posting."})

        if self.dead_tree_count is None or self.dead_tree_count <= 0:
            raise ValidationError({"dead_tree_count": "Dead tree count must be strictly positive."})

        if self.impairment_value is None or self.impairment_value <= 0:
            raise ValidationError({"impairment_value": "Impairment value must be strictly positive."})

        stock = self.location_tree_stock
        if stock and stock.location_id and stock.location.farm_id != self.farm_id:
            raise ValidationError({"location_tree_stock": "Location tree stock must belong to the same farm."})

        if stock and self.dead_tree_count and self.dead_tree_count > (stock.current_tree_count or 0):
            raise ValidationError({"dead_tree_count": "Dead tree count cannot exceed the current tree stock."})

        if self.is_posted and not self.authorized_by_id:
            raise ValidationError({"authorized_by": "Authorized approver is required before posting an impairment."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
