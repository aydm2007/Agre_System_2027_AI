from datetime import date
from decimal import Decimal
from django.db import models
from django.db.models import Q, F
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from .base import SoftDeleteModel
from .farm import Farm, Location
from .crop import Crop
from .inventory import Item, Unit
from .task import Task
from .rls_scope import get_rls_user_id
from smart_agri.core.constants import StandardUOM


class CropPlanScopedQuerySet(models.QuerySet):
    def for_rls_user(self):
        user_id = get_rls_user_id()
        if user_id is None or user_id == -1:
            return self
        return self.filter(farm__memberships__user_id=user_id).distinct()


class CropPlanScopedManager(models.Manager):
    def get_queryset(self):
        return CropPlanScopedQuerySet(self.model, using=self._db).for_rls_user()

class Season(models.Model):
    """
    Agricultural season definition (e.g., Spring 2026, Summer 2026).
    
    MANAGED=True (Updated 2026-01-28):
    - Changed from managed=False to managed=True for AGRI-MAESTRO compliance
    - Table 'core_season' is now fully managed by Django
    - Schema changes tracked via Django migrations
    - AGRI-MAESTRO Rule: All core models must be managed=True
    """
    name = models.CharField(max_length=100)
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = True  # ✅ AGRI-MAESTRO Compliance
        db_table = 'core_season'
        ordering = ['-start_date']
        verbose_name = "موسم زراعي"
        verbose_name_plural = "المواسم الزراعية"

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError("تاريخ الانتهاء يجب أن يكون بعد تاريخ البدء.")

class CropTemplate(SoftDeleteModel):
    CATEGORY_SERVICE = "service"
    CATEGORY_MATERIAL = "material"
    CATEGORY_BUNDLE = "bundle"
    CATEGORY_CHOICES = [
        (CATEGORY_SERVICE, "Service"),
        (CATEGORY_MATERIAL, "Material"),
        (CATEGORY_BUNDLE, "Bundle"),
    ]

    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name="templates")
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default=CATEGORY_BUNDLE)
    description = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("crop", "name", "category")
        indexes = [models.Index(fields=["crop", "category"])]
        verbose_name = "قالب محصول"
        verbose_name_plural = "قوالب المحاصيل"

    def __str__(self):
        return f"{self.crop} / {self.name}"

class CropTemplateTask(SoftDeleteModel):
    template = models.ForeignKey(CropTemplate, on_delete=models.CASCADE, related_name="tasks")
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True, related_name="template_links")
    stage = models.CharField(max_length=50, blank=True, default="")
    name = models.CharField(max_length=200)
    days_offset = models.PositiveIntegerField(
        default=0, 
        help_text="اليوم الذي تبدأ فيه المهمة (نسبة لبداية الخطة)"
    )
    duration_days = models.PositiveIntegerField(
        default=1, 
        help_text="المدة المتوقعة للمهمة بالأيام"
    )
    estimated_hours = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    notes = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        indexes = [models.Index(fields=["template", "name"])]

class CropTemplateMaterial(SoftDeleteModel):
    template = models.ForeignKey(CropTemplate, on_delete=models.CASCADE, related_name="materials")
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="template_materials")
    qty = models.DecimalField(max_digits=12, decimal_places=3)
    unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True, related_name="template_materials")
    uom = models.CharField(max_length=40, blank=True, default="")
    cost_override = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    notes = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        unique_together = ("template", "item")
        indexes = [models.Index(fields=["template", "item"])]

    def clean(self):
        super().clean()
        if self.qty is None or self.qty <= 0:
            raise ValidationError({"qty": "الكمية يجب أن تكون أكبر من الصفر."})

class CropPlanLocation(SoftDeleteModel):
    crop_plan = models.ForeignKey('CropPlan', on_delete=models.CASCADE, related_name="plan_locations")
    location = models.ForeignKey(Location, on_delete=models.RESTRICT, related_name="plan_allocations")
    assigned_area = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    class Meta:
        managed = True
        db_table = 'core_cropplan_location'
        verbose_name = "موقع الخطة"
        verbose_name_plural = "مواقع الخطط"
        constraints = [
            models.UniqueConstraint(
                fields=["crop_plan", "location"],
                condition=Q(deleted_at__isnull=True),
                name="cropplanlocation_unique_active"
            )
        ]

class CropPlan(SoftDeleteModel):
    def __init__(self, *args, **kwargs):
        legacy_date_planted = kwargs.pop("date_planted", None)
        if legacy_date_planted and "start_date" not in kwargs:
            kwargs["start_date"] = legacy_date_planted
        legacy_season = kwargs.get("season")
        if isinstance(legacy_season, str):
            season_name = legacy_season.strip() or str(date.today().year)
            try:
                year = int(season_name)
            except ValueError:
                year = date.today().year
            season_obj, _ = Season.objects.get_or_create(
                name=season_name,
                defaults={
                    "start_date": date(year, 1, 1),
                    "end_date": date(year, 12, 31),
                    "is_active": True,
                },
            )
            kwargs["season"] = season_obj
        super().__init__(*args, **kwargs)

    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="crop_plans")
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name="crop_plans")
    name = models.CharField(max_length=200)
    template = models.ForeignKey(
        CropTemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name="generated_plans"
    )
    # [ULTIMATE EDITION] Agronomic Recipe / BOM integration for Strict Standard Costing
    recipe = models.ForeignKey(
        'core.CropRecipe', on_delete=models.RESTRICT, null=True, blank=True, related_name="applied_plans",
        help_text="الوصفة الزراعية المعيارية المعتمدة لهذه الخطة (BOM)"
    )

    start_date = models.DateField()
    end_date = models.DateField()
    area = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    season = models.ForeignKey(Season, on_delete=models.SET_NULL, null=True, blank=True, related_name="crop_plans")
    currency = models.CharField(max_length=8, default="YER")
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="crop_plans_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="crop_plans_updated",
    )
    
    budget_materials = models.DecimalField(max_digits=19, decimal_places=4, default=Decimal("0.0000"))
    budget_labor = models.DecimalField(max_digits=19, decimal_places=4, default=Decimal("0.0000"))
    budget_machinery = models.DecimalField(max_digits=19, decimal_places=4, default=Decimal("0.0000"))
    budget_total = models.DecimalField(max_digits=19, decimal_places=4, default=Decimal("0.0000"))
    
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="crop_plans_approved",
    )
    locked_at = models.DateTimeField(null=True, blank=True)
    expected_yield = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    budget_amount = models.DecimalField(max_digits=19, decimal_places=4, default=Decimal("0.0000"))
    yield_unit = models.CharField(max_length=40, blank=True, default="")

    from smart_agri.core.constants import CropPlanStatus
    status = models.CharField(
        max_length=20, 
        choices=CropPlanStatus.choices, 
        default=CropPlanStatus.ACTIVE, 
        db_index=True
    )

    objects = CropPlanScopedManager()

    class Meta:
        managed = True
        db_table = 'core_cropplan'
        verbose_name = "خطة زراعية"
        verbose_name_plural = "الخطط الزراعية"
        # AGRI-GUARDIAN: Constraints
        constraints = [
            models.CheckConstraint(check=Q(start_date__lte=F("end_date")), name="cropplan_valid_dates"),
            # The UniqueConstraint cropplan_unique_production_unit was removed.
            # Overlapping crop plans validation is now governed by FarmSettings (allow_overlapping_crop_plans).
        ]
        indexes = [
            models.Index(fields=["farm", "start_date"]),
            models.Index(fields=["farm", "season"]),
            models.Index(fields=["status"]),
            models.Index(fields=["crop", "season"]),
        ]

    def __str__(self):
        return f"{self.farm.name} / {self.name}"

    def save(self, *args, **kwargs):
        # Legacy compatibility for tests/seeds that only pass farm + area + date_planted.
        if not self.start_date:
            self.start_date = timezone.localdate()
        if not self.end_date:
            self.end_date = self.start_date
        if not self.name:
            self.name = f"Plan {self.start_date}"
        if not self.crop_id:
            crop, _ = Crop.objects.get_or_create(name="Legacy Crop", mode="Open")
            self.crop = crop
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        for field_name in ["budget_materials", "budget_labor", "budget_machinery", "budget_total"]:
            value = getattr(self, field_name, None)
            if value is not None and value < 0:
                raise ValidationError({field_name: "لا يمكن أن تكون الميزانية سالبة."})

        # --- Governance & Integrity: Overlapping Plans Rule --- #
        if self.farm_id and self.season_id and self.crop_id and not self.deleted_at:
            # [AGRI-GUARDIAN] Exact Date Collision Check (User Requested)
            identical_starts = CropPlan.objects.filter(
                farm_id=self.farm_id,
                crop_id=self.crop_id,
                start_date=self.start_date,
                deleted_at__isnull=True
            )
            if self.pk:
                identical_starts = identical_starts.exclude(pk=self.pk)
            
            if identical_starts.exists():
                raise ValidationError({
                    "start_date": "🔴 لا يمكن إضافة خطة لنفس المحصول بنفس تاريخ البداية. يوجد خطة مسجلة مسبقاً في هذا اليوم."
                })

            # Check FarmSettings policies for general overlap
            try:
                farm_settings = self.farm.settings
                allow_overlap = farm_settings.allow_overlapping_crop_plans
            except (AttributeError, LookupError):
                allow_overlap = False  # Default to strict if settings not found
            
            if not allow_overlap:
                overlapping_plans = CropPlan.objects.filter(
                    farm_id=self.farm_id,
                    season_id=self.season_id,
                    crop_id=self.crop_id,
                    deleted_at__isnull=True
                )
                if self.pk:
                    overlapping_plans = overlapping_plans.exclude(pk=self.pk)
                
                if overlapping_plans.exists():
                    raise ValidationError(
                        "🔴 [POLICY EXCEPTION] السياسات الحالية تمنع وجود أكثر من خطة نشطة لنفس المحصول والموسم. "
                        "يرجى تفعيل (إمكانية تعدد الخطط) من شاشة إعدادات المزرعة/الحوكمة."
                    )

            # --- Governance & Integrity: Sharecropping Isolation --- #
            # A CropPlan CANNOT be created if there is an active SharecroppingContract for the same crop/season.
            from smart_agri.core.models.partnerships import SharecroppingContract
            has_sharecrop = SharecroppingContract.objects.filter(
                farm_id=self.farm_id,
                season_id=self.season_id,
                crop_id=self.crop_id,
                is_active=True,
                deleted_at__isnull=True
            ).exists()
            if has_sharecrop:
                raise ValidationError(
                    "🔴 [FORENSIC BLOCK] لا يمكن إنشاء خطة عمل (أعمال فنية) لمحصول مؤجر أو يدار بنظام الشراكة في نفس الموسم."
                )

    @property
    def projected_yield(self):
        return 0

    @property
    def actual_cost(self):
        from .activity import Activity
        return Activity.objects.filter(
            crop_plan=self,
            deleted_at__isnull=True
        ).aggregate(total=models.Sum('cost_total'))['total'] or Decimal('0')

    @property
    def total_revenue(self):
        from .activity import ActivityHarvest
        from .crop import CropProduct
        import logging
        
        logger = logging.getLogger(__name__)
        
        harvests = ActivityHarvest.objects.filter(
            activity__crop_plan=self,
            activity__deleted_at__isnull=True
        ).select_related('activity__product', 'activity__product__item')  # FIX: N+1 Query
        
        total = Decimal('0')
        for h in harvests:
            try:
                if h.activity.product and h.activity.product.item and h.activity.product.item.unit_price:
                    total += (h.harvest_quantity * h.activity.product.item.unit_price)
            except (AttributeError, TypeError) as e:
                logger.warning(f"Revenue calculation error for harvest {h.pk}: {e}")
                continue  # Skip this harvest but log the issue
        return total

    @property
    def roi(self):
        cost = self.actual_cost
        revenue = self.total_revenue
        if cost == 0: return 0
        return ((revenue - cost) / cost) * 100

class PlannedActivity(SoftDeleteModel):
    crop_plan = models.ForeignKey(CropPlan, on_delete=models.CASCADE, related_name="planned_activities")
    task = models.ForeignKey(Task, on_delete=models.PROTECT, related_name="planned_instances")
    planned_date = models.DateField(help_text="Legacy date reference")
    expected_date_start = models.DateField(null=True, blank=True)
    expected_date_end = models.DateField(null=True, blank=True)
    estimated_hours = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    notes = models.CharField(max_length=250, blank=True, default="")

    class Meta:
        ordering = ["planned_date"]
        indexes = [models.Index(fields=["crop_plan", "planned_date"])]

class PlannedMaterial(SoftDeleteModel):
    crop_plan = models.ForeignKey(CropPlan, on_delete=models.CASCADE, related_name="planned_materials")
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="planned_usages")
    planned_qty = models.DecimalField(max_digits=12, decimal_places=3)
    unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True, related_name="planned_materials")
    uom = models.CharField(max_length=40, choices=StandardUOM.choices, blank=True, default="")

    class Meta:
        unique_together = ("crop_plan", "item")
        indexes = [models.Index(fields=["crop_plan"]), models.Index(fields=["item"])]

class CropPlanBudgetLine(SoftDeleteModel):
    CATEGORY_MATERIALS = "materials"
    CATEGORY_LABOR = "labor"
    CATEGORY_MACHINERY = "machinery"
    CATEGORY_OTHER = "other"
    CATEGORY_CHOICES = [
        (CATEGORY_MATERIALS, "Materials"),
        (CATEGORY_LABOR, "Labor"),
        (CATEGORY_MACHINERY, "Machinery"),
        (CATEGORY_OTHER, "Other"),
    ]

    crop_plan = models.ForeignKey(CropPlan, on_delete=models.CASCADE, related_name="budget_lines")
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True, related_name="budget_lines")
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default=CATEGORY_OTHER)
    qty_budget = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    uom = models.CharField(max_length=40, choices=StandardUOM.choices, blank=True, default="")
    rate_budget = models.DecimalField(max_digits=19, decimal_places=4, default=Decimal("0.0000"))
    total_budget = models.DecimalField(max_digits=19, decimal_places=4, default=Decimal("0.0000"))
    currency = models.CharField(max_length=8, blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["crop_plan", "task"]),
            models.Index(fields=["crop_plan", "category"]),
        ]
        verbose_name = "بند موازنة الخطة"
        verbose_name_plural = "بنود موازنة الخطة"
        constraints = [
            models.UniqueConstraint(
                fields=["crop_plan", "task", "category"],
                condition=Q(deleted_at__isnull=True),
                name="cropplanbudgetline_unique_active",
            )
        ]

class PlanImportLog(SoftDeleteModel):
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    crop_plan = models.ForeignKey(CropPlan, on_delete=models.CASCADE, related_name="import_logs")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="plan_imports_created"
    )
    status = models.CharField(max_length=20, default=STATUS_SUCCESS)
    summary = models.JSONField(default=dict, blank=True)
    file_name = models.CharField(max_length=255, blank=True, default="")
    imported_count = models.IntegerField(default=0)
    skipped_count = models.IntegerField(default=0)
    errors = models.JSONField(default=list, blank=True)
    dry_run = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["crop_plan"], name="planimportlog_plan_idx"),
            models.Index(fields=["created_at"], name="planimportlog_created_idx"),
        ]

class Budget(SoftDeleteModel):
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE)
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    crop = models.ForeignKey(Crop, on_delete=models.SET_NULL, null=True, blank=True)
    category = models.CharField(max_length=100, db_index=True)
    amount_allocated = models.DecimalField(max_digits=14, decimal_places=2)
    notes = models.TextField(blank=True)

    class Meta:
        managed = True
        db_table = 'core_budget'
        verbose_name = "موازنة"
        verbose_name_plural = "الموازنات"
        unique_together = ('farm', 'season', 'crop', 'category')
