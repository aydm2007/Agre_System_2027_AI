from datetime import date
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateRangeField
from django.contrib.postgres.fields.ranges import RangeOperators
from django.core.exceptions import ValidationError
from smart_agri.core.models.base import SoftDeleteModel, SoftDeleteQuerySet
from smart_agri.core.models.rls_scope import get_rls_user_id
from smart_agri.core.constants import AssetStatus


class FarmScopedQuerySet(SoftDeleteQuerySet):
    def order_by(self, *field_names):
        mapped = []
        for field in field_names:
            if field == "code":
                mapped.append("slug")
            elif field == "-code":
                mapped.append("-slug")
            else:
                mapped.append(field)
        return super().order_by(*mapped)

    def for_rls_user(self):
        user_id = get_rls_user_id()
        if user_id is None or user_id == -1:
            return self
        return self.filter(memberships__user_id=user_id).distinct()


class FarmScopedManager(models.Manager.from_queryset(FarmScopedQuerySet)):
    def get_queryset(self):
        return super().get_queryset().for_rls_user()


class LocationScopedQuerySet(SoftDeleteQuerySet):
    def for_rls_user(self):
        user_id = get_rls_user_id()
        if user_id is None or user_id == -1:
            return self
        return self.filter(farm__memberships__user_id=user_id).distinct()


class LocationScopedManager(models.Manager.from_queryset(LocationScopedQuerySet)):
    def get_queryset(self):
        return super().get_queryset().for_rls_user()

class Farm(SoftDeleteModel):
    def __init__(self, *args, **kwargs):
        kwargs.pop("owner", None)
        legacy_code = kwargs.pop("code", None)
        legacy_total_area = kwargs.pop("total_area", None)
        if legacy_code:
            self._legacy_code = str(legacy_code)
            if not kwargs.get("slug"):
                kwargs["slug"] = str(legacy_code)
        if legacy_total_area is not None and "area" not in kwargs:
            kwargs["area"] = legacy_total_area
        super().__init__(*args, **kwargs)

    ZAKAT_HALF_TITHE = '5_PERCENT'
    ZAKAT_TITHE = '10_PERCENT'
    ZAKAT_CHOICES = [
        (ZAKAT_HALF_TITHE, 'نصف العشر (5%) - آبار/مضخات'),
        (ZAKAT_TITHE, 'العشر (10%) - مطر/سدود/غيل'),
    ]

    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=150)
    region = models.CharField(max_length=100)
    
    TIER_SMALL = 'SMALL'
    TIER_MEDIUM = 'MEDIUM'
    TIER_LARGE = 'LARGE'
    TIER_CHOICES = [
        (TIER_SMALL, 'صغيرة (<50)'),
        (TIER_MEDIUM, 'متوسطة (50-249)'),
        (TIER_LARGE, 'كبيرة (>=250)'),
    ]
    tier = models.CharField(
        max_length=10, 
        choices=TIER_CHOICES, 
        default=TIER_SMALL,
        help_text="تصنيف المزرعة لتحديد قالب الصلاحيات (RACI)"
    )

    area = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    zakat_rule = models.CharField(
        max_length=20,
        choices=ZAKAT_CHOICES,
        default=ZAKAT_HALF_TITHE,
        help_text="يحدد نسبة الزكاة الشرعية: 5% للكلفة، 10% للمطر.",
    )

    # [AGRI-GUARDIAN] Missing Fields Restoration for Schema Parity
    is_organization = models.BooleanField(default=False)
    operational_mode = models.CharField(max_length=50, default='SIMPLE')
    sensing_mode = models.CharField(max_length=50, default='MANUAL')
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='sub_farms')
    organization_id = models.IntegerField(null=True, blank=True)

    class Meta:
        managed = True
        db_table = 'core_farm'
        verbose_name = "مزرعة"
        verbose_name_plural = "المزارع"
        constraints = [
            models.UniqueConstraint(
                fields=['name'],
                condition=Q(deleted_at__isnull=True),
                name='unique_farm_name_active'
            ),
            models.UniqueConstraint(
                fields=['slug'],
                condition=Q(deleted_at__isnull=True),
                name='unique_farm_slug_active'
            ),
        ]

    objects = FarmScopedManager()

    def clean(self):
        """
        [AGRI-GUARDIAN §Axis-10] Auto-classify farm tier based on area.
        If area is set, tier is enforced dynamically:
          - area < 50      → SMALL
          - 50 ≤ area < 250 → MEDIUM
          - area ≥ 250     → LARGE
        If area is null, tier remains as manually set.
        """
        super().clean()
        if self.area is not None:
            from decimal import Decimal
            area_val = Decimal(str(self.area))
            if area_val < Decimal('50'):
                self.tier = self.TIER_SMALL
            elif area_val < Decimal('250'):
                self.tier = self.TIER_MEDIUM
            else:
                self.tier = self.TIER_LARGE

    def save(self, *args, **kwargs):
        # Auto-classify tier on every save if area is set
        if self.area is not None:
            from decimal import Decimal
            area_val = Decimal(str(self.area))
            if area_val < Decimal('50'):
                self.tier = self.TIER_SMALL
            elif area_val < Decimal('250'):
                self.tier = self.TIER_MEDIUM
            else:
                self.tier = self.TIER_LARGE
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def code(self):
        stored = getattr(self, "_legacy_code", None)
        if stored:
            return stored
        slug_value = (self.slug or "").strip()
        if not slug_value:
            return ""
        parts = [part for part in slug_value.split("-") if part]
        if len(parts) >= 2:
            return "".join(part[0] for part in parts).upper()
        return slug_value.upper()

    @code.setter
    def code(self, value):
        self.slug = value

class Location(SoftDeleteModel):
    def __init__(self, *args, **kwargs):
        legacy_short_code = kwargs.pop("short_code", None)
        if legacy_short_code and "code" not in kwargs:
            kwargs["code"] = legacy_short_code
        super().__init__(*args, **kwargs)

    TYPE_CHOICES = [
        ("Protected", "Protected"),
        ("Field", "Field"),
        ("Orchard", "Orchard"),
        ("Grain", "Grain"),
        ("Service", "Service"),
        ("Store", "مخزن"),
        ("Warehouse", "مستودع مركزي"),
        ("Transit", "عهدة قيد التسليم"),
        ("Custody", "مخزن عهدة"),
    ]

    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="locations")
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="Field")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    code = models.CharField(max_length=50, blank=True, null=True)

    objects = LocationScopedManager()

    class Meta:
        unique_together = ("farm", "name")
        indexes = [models.Index(fields=["farm", "type"])]
        verbose_name = "موقع"
        verbose_name_plural = "المواقع"

    def __str__(self):
        return f"{self.farm.name} / {self.name}"


class LocationIrrigationPolicy(SoftDeleteModel):
    ZAKAT_RAIN_10 = "RAIN_10"
    ZAKAT_WELL_5 = "WELL_5"
    ZAKAT_MIXED_75 = "MIXED_75"
    ZAKAT_CHOICES = [
        (ZAKAT_RAIN_10, "Rain-fed 10%"),
        (ZAKAT_WELL_5, "Well/Pump 5%"),
        (ZAKAT_MIXED_75, "Mixed 7.5%"),
    ]

    location = models.ForeignKey(
        "Location",
        on_delete=models.CASCADE,
        related_name="irrigation_policies",
    )
    zakat_rule = models.CharField(max_length=20, choices=ZAKAT_CHOICES)
    valid_daterange = DateRangeField(
        help_text="Effective business date range for this policy.",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_irrigation_policies",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    reason = models.CharField(max_length=500)

    class Meta:
        db_table = "core_location_irrigation_policy"
        verbose_name = "سياسة ري"
        verbose_name_plural = "سياسات الري"
        indexes = [
            models.Index(fields=["location", "is_active"], name="loc_irrig_policy_active_idx"),
        ]
        constraints = [
            ExclusionConstraint(
                name="loc_irrig_policy_no_overlap",
                expressions=[
                    ("location", RangeOperators.EQUAL),
                    ("valid_daterange", RangeOperators.OVERLAPS),
                ],
                condition=Q(is_active=True, deleted_at__isnull=True),
            ),
        ]

    @property
    def farm_id(self):
        return getattr(self.location, "farm_id", None)

    @property
    def valid_from(self):
        if not self.valid_daterange:
            return None
        return self.valid_daterange.lower

    @property
    def valid_to(self):
        if not self.valid_daterange:
            return None
        return self.valid_daterange.upper

    def clean(self):
        super().clean()
        if not self.reason or not str(self.reason).strip():
            raise ValidationError({"reason": "Policy reason is required."})
        if not self.valid_daterange:
            raise ValidationError({"valid_daterange": "Valid date range is required."})
        if self.valid_daterange.lower is None:
            raise ValidationError({"valid_daterange": "Lower bound (valid_from) is required."})
        if (
            self.valid_daterange.upper is not None
            and self.valid_daterange.upper <= self.valid_daterange.lower
        ):
            raise ValidationError({"valid_daterange": "Upper bound must be greater than lower bound."})

    def save(self, *args, **kwargs):
        if self.is_active and self.approved_at is None:
            self.approved_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        start = self.valid_from.isoformat() if isinstance(self.valid_from, date) else "?"
        end = self.valid_to.isoformat() if isinstance(self.valid_to, date) else "open"
        return f"{self.location} [{self.zakat_rule}] {start} -> {end}"

class Asset(SoftDeleteModel):
    # choices for category...

    CATEGORY_CHOICES = [
        ("Well", "بئر مياه"),
        ("Machinery", "معدات/آليات"),
        ("Irrigation", "أنظمة ري"),
        ("Solar", "طاقة شمسية"),
        ("Vehicle", "مركبات/سيارات"),
        ("Facility", "مرافق/مبانى"),
        ("Fuel", "خزانات وقود"),
    ]

    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="assets", verbose_name="المزرعة")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, verbose_name="تصنيف الأصل")
    code = models.CharField(max_length=60, blank=True, default="", verbose_name="كود الأصل")
    name = models.CharField(max_length=200, verbose_name="اسم الأصل")
    asset_type = models.CharField(max_length=50, db_index=True, default="general", verbose_name="النوع التقني")
    purchase_date = models.DateField(auto_now_add=True, db_index=True, verbose_name="تاريخ الشراء")
    purchase_value = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="القيمة الشرائية")
    status = models.CharField(max_length=50, default=AssetStatus.ACTIVE, choices=AssetStatus.choices, verbose_name="الحالة التشغيلية")
    
    # [Protocol XVI] Asset Lifecycle & Depreciation (IAS 16)
    salvage_value = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Estimated value at end of life", verbose_name="القيمة التخريدية (الخردة)")
    useful_life_years = models.PositiveIntegerField(default=5, help_text="Depreciation period in years", verbose_name="العمر الافتراضي (سنوات)")
    METHOD_STRAIGHT_LINE = 'SL'
    METHOD_DECLINING = 'DB'
    DEPRECIATION_CHOICES = [
        (METHOD_STRAIGHT_LINE, 'القسط الثابت'),
        (METHOD_DECLINING, 'القسط المتناقص'),
    ]
    depreciation_method = models.CharField(max_length=3, choices=DEPRECIATION_CHOICES, default=METHOD_STRAIGHT_LINE, verbose_name="طريقة الإهلاك")
    accumulated_depreciation = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False, verbose_name="مجمع الإهلاك")

    # [AGRI-GUARDIAN] Machine Costing
    operational_cost_per_hour = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0, 
        help_text="تكلفة التشغيل التقديرية لكل ساعة (وقود + صيانة)",
        verbose_name="تكلفة التشغيل للساعة"
    )



    class Meta:
        managed = True
        db_table = 'core_asset'
        verbose_name = "أصل"
        verbose_name_plural = "الأصول"
        indexes = [models.Index(fields=["farm", "category"], name="asset_farm_category_idx")]
        constraints = [
            models.UniqueConstraint(
                fields=("farm", "code"),
                condition=Q(code__gt=""),
                name="asset_unique_code_per_farm",
            )
        ]

    def __str__(self):
        code = f"[{self.code}] " if self.code else ""
        return f"{self.farm.name} / {self.category} / {code}{self.name}"

class LocationWell(SoftDeleteModel):
    location = models.OneToOneField(
        'Location', 
        on_delete=models.CASCADE, 
        related_name='well_details',
        db_column='location_id'
    )
    asset = models.ForeignKey(
        'Asset',
        on_delete=models.CASCADE,
        related_name='location_assignments',
        limit_choices_to={'category': 'Well'}
    )
    well_depth = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    pump_type = models.CharField(max_length=100, blank=True, null=True)
    capacity_lps = models.DecimalField(
        max_digits=10, decimal_places=2, 
        null=True, blank=True, 
        help_text="Capacity in Liters per Second"
    )
    
    # from smart_agri.core.constants import AssetStatus
    status = models.CharField(max_length=20, choices=AssetStatus.choices, default=AssetStatus.ACTIVE)
    is_operational = models.BooleanField(default=True)
    last_serviced_at = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    @property
    def depth_meters(self):
        return self.well_depth

    @depth_meters.setter
    def depth_meters(self, value):
        self.well_depth = value

    @property
    def discharge_rate_lps(self):
        return self.capacity_lps

    @discharge_rate_lps.setter
    def discharge_rate_lps(self, value):
        self.capacity_lps = value

    class Meta:
        managed = True
        db_table = 'core_location_well'
        verbose_name = "تكوين بئر"
        verbose_name_plural = "تكوينات الآبار"
        constraints = [
            models.UniqueConstraint(
                fields=['location', 'asset'],
                condition=Q(deleted_at__isnull=True),
                name='unique_location_well_asset_active'
            )
        ]

    def __str__(self):
        return f"{self.location} -> {self.asset} ({self.get_status_display()})"


class SolarAssetManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(category="Solar")


class SolarAsset(Asset):
    """
    نموذج وكيل (Proxy Model) مخصص لأصول الطاقة الشمسية.
    يفصل المنطق التشغيلي الخاص بالطاقة الشمسية ويتوافق مع معايير Agri-Guardian (المحور 9).
    """
    objects = SolarAssetManager()

    class Meta:
        proxy = True
        verbose_name = "أصل طاقة شمسية"
        verbose_name_plural = "أصول الطاقة الشمسية"

    def calculate_operational_depreciation(self, hours):
        from smart_agri.core.services.asset_service import AssetService
        from decimal import Decimal
        return AssetService.calculate_operational_solar_depreciation(self, Decimal(str(hours)))

class AssetTransfer(SoftDeleteModel):
    """
    [AGRI-GUARDIAN Phase 5] Asset Transfer Evidence Record.
    Automates the transfer of an asset from one farm to another with a formal approval workflow.
    Ensures Chain of Custody integrity.
    """
    STATUS_PENDING = "PENDING"
    STATUS_APPROVED = "APPROVED"
    STATUS_REJECTED = "REJECTED"
    
    STATUS_CHOICES = [
        (STATUS_PENDING, "معلق للرد"),
        (STATUS_APPROVED, "تم الاعتماد والنقل"),
        (STATUS_REJECTED, "مرفوض"),
    ]

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="transfer_history")
    from_farm = models.ForeignKey(Farm, on_delete=models.PROTECT, related_name="transfers_out")
    to_farm = models.ForeignKey(Farm, on_delete=models.PROTECT, related_name="transfers_in")
    
    justification = models.CharField(max_length=500, help_text="مبرر نقل الأصل/الآلية")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="asset_transfers_requested")
    requested_at = models.DateTimeField(auto_now_add=True)
    
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="asset_transfers_approved")
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=500, blank=True, default="")
    
    class Meta:
        managed = True
        db_table = 'core_asset_transfer'
        verbose_name = "تذكرة نقل أصل"
        verbose_name_plural = "تذاكر نقل الأصول"
        ordering = ['-requested_at']

    def clean(self):
        super().clean()
        if self.from_farm_id == self.to_farm_id:
            raise ValidationError("Farm boundaries violation: Cannot transfer an asset to the same farm.")

    def __str__(self):
        return f"نقل: {self.asset.name} من {self.from_farm.name} إلى {self.to_farm.name}"

class AssetBatchMaintenance(SoftDeleteModel):
    """
    [AGRI-GUARDIAN Phase 5] Batch Maintenance Record (Machine Card).
    Aggregates multiple maintenance operations (spare parts, oil, mechanic fees)
    into a single approved batch to update the machine's running cost.
    """
    STATUS_DRAFT = "DRAFT"
    STATUS_APPROVED = "APPROVED"
    
    STATUS_CHOICES = [
        (STATUS_DRAFT, "مسودة"),
        (STATUS_APPROVED, "معتمد ومرحَّل"),
    ]

    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="maintenance_batches")
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="maintenance_batches")
    
    maintenance_date = models.DateField(default=timezone.now)
    description = models.CharField(max_length=500, help_text="وصف دورة الصيانة (مثال: عمرة محرك رئيسية)")
    
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="إجمالي التكلفة المجمعة")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="maintenance_batches_created")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="maintenance_batches_approved")
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = True
        db_table = 'core_asset_batch_maintenance'
        verbose_name = "سجل صيانة مجمعة"
        verbose_name_plural = "سجلات الصيانة المجمعة"
        ordering = ['-maintenance_date']

    def clean(self):
        super().clean()
        if self.asset.farm_id != self.farm_id:
            raise ValidationError("Asset does not belong to the selected farm.")
        if self.total_cost < 0:
            raise ValidationError("Total cost cannot be negative.")

    def __str__(self):
        return f"صيانة شاملة: {self.asset.name} - {self.maintenance_date} - {self.total_cost}"

class AssetBatchMaintenanceLine(SoftDeleteModel):
    """
    [AGRI-GUARDIAN Phase 5] Detailed maintenance items (spare parts, oil, mechanic) 
    related to a single batch maintenance operation.
    """
    batch = models.ForeignKey(AssetBatchMaintenance, on_delete=models.CASCADE, related_name="lines")
    description = models.CharField(max_length=255, help_text="وصف البند (مثال: فلتر زيت، أجر فني)")
    cost = models.DecimalField(max_digits=12, decimal_places=2, help_text="تكلفة البند")
    
    # Optional link to inventory if parts were consumed from store
    inventory_transaction_id = models.IntegerField(null=True, blank=True)

    class Meta:
        managed = True
        db_table = 'core_asset_batch_maintenance_line'
        verbose_name = "بند صيانة"
        verbose_name_plural = "بنود الصيانة"
        ordering = ['id']

    def clean(self):
        super().clean()
        if self.cost < 0:
            raise ValidationError("Line cost cannot be negative.")

    def __str__(self):
        return f"{self.description} - {self.cost}"
