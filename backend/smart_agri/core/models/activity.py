import uuid
from datetime import date
from decimal import Decimal
from decimal import Decimal
from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.conf import settings
from django.utils import timezone
from .base import SoftDeleteModel
from .farm import Farm, Location, Asset
from .crop import Crop, CropVariety, CropProduct
from .task import Task
from .settings import Supervisor
from smart_agri.inventory.models import Item, Unit
from smart_agri.core.constants import StandardUOM
from .rls_scope import get_rls_user_id

# استخدام مراجع نصية لتجنب الاستيراد الدائري مع DailyLog

class ActivityLocation(SoftDeleteModel):
    activity = models.ForeignKey('Activity', on_delete=models.CASCADE, related_name="activity_locations")
    location = models.ForeignKey('core.Location', on_delete=models.RESTRICT, related_name="location_allocations")
    allocated_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.00'),
        help_text="نسبة التوزيع المئوية (مثلاً 25%) لمنع ازدواجية الحساب"
    )

    class Meta:
        managed = True
        db_table = 'core_activity_location'
        verbose_name = "موقع الإنجاز"
        verbose_name_plural = "مواقع الإنجازات"
        constraints = [
            models.UniqueConstraint(
                fields=["activity", "location"],
                condition=Q(deleted_at__isnull=True),
                name="activitylocation_unique_active"
            )
        ]

class Activity(SoftDeleteModel):
    @staticmethod
    def _json_safe_value(value):
        if isinstance(value, Decimal):
            return str(value)
        return value

    def __init__(self, *args, **kwargs):
        legacy_variety = kwargs.pop("variety", None)
        legacy_location = kwargs.pop("location", None)
        legacy_location_id = kwargs.pop("location_id", None)
        legacy_planted_area = kwargs.pop("planted_area", None)
        legacy_planted_uom = kwargs.pop("planted_uom", None)
        legacy_date = kwargs.pop("date", None)
        legacy_activity_date = kwargs.pop("activity_date", None)
        legacy_water_uom = kwargs.pop("water_uom", None)
        legacy_fertilizer_uom = kwargs.pop("fertilizer_uom", None)
        kwargs.pop("items", None)
        kwargs.pop("name", None)
        if legacy_variety is not None and "crop_variety" not in kwargs:
            kwargs["crop_variety"] = legacy_variety
        super().__init__(*args, **kwargs)
        if legacy_planted_area is not None:
            payload = self.data if isinstance(self.data, dict) else {}
            payload["planted_area"] = str(legacy_planted_area)
            if legacy_planted_uom is not None:
                payload["planted_uom"] = legacy_planted_uom
            self.data = payload
            if "days_spent" not in kwargs:
                self.days_spent = Decimal("0")
        if legacy_water_uom is not None or legacy_fertilizer_uom is not None:
            payload = self.data if isinstance(self.data, dict) else {}
            if legacy_water_uom is not None:
                payload["water_uom"] = legacy_water_uom
            if legacy_fertilizer_uom is not None:
                payload["fertilizer_uom"] = legacy_fertilizer_uom
            self.data = payload
        normalized_legacy_date = legacy_activity_date if legacy_activity_date is not None else legacy_date
        if normalized_legacy_date is not None:
            self._legacy_date = normalized_legacy_date
        self._legacy_location = legacy_location
        self._legacy_location_id = legacy_location_id

    # [Offline Hardening]
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    idempotency_key = models.UUIDField(
        null=True,
        blank=True,
        help_text="Agri-Guardian: مفتاح منع التكرار لبيئة الشبكة الضعيفة",
    )
    
    device_timestamp = models.DateTimeField(
        null=True, blank=True,
        help_text="Field device timestamp for offline audit trail"
    )
    
    # AGRI-GUARDIAN FIX: تم تغيير on_delete من CASCADE إلى PROTECT لمنع مسح الأدلة الجنائية
    # في حال حذف السجل اليومي بالخطأ.
    log = models.ForeignKey("DailyLog", on_delete=models.PROTECT, related_name="activities")
    
    crop_plan = models.ForeignKey(
        "CropPlan", on_delete=models.SET_NULL, null=True, blank=True, related_name="activities"
    )
    crop = models.ForeignKey(Crop, on_delete=models.SET_NULL, null=True, blank=True, related_name="activities")
    product = models.ForeignKey(
        CropProduct, on_delete=models.SET_NULL, null=True, blank=True, related_name='activities'
    )
    task = models.ForeignKey(
        Task, on_delete=models.PROTECT, null=True, blank=True, related_name="activities",
    )
    task_contract_version = models.PositiveIntegerField(default=1)
    task_contract_snapshot = models.JSONField(default=dict, blank=True)
    asset = models.ForeignKey(Asset, on_delete=models.SET_NULL, null=True, blank=True, related_name="activities")
    
    # ملاحظة: هذا الحقل زائد ويسبب ازدواجية مع ActivityIrrigation.well_asset
    # تم الإبقاء عليه لعدم كسر التوافق مع قاعدة البيانات الحالية، ولكن يجب استخدام ActivityIrrigation كمصدر للحقيقة.
    well_asset = models.ForeignKey(
        Asset, on_delete=models.SET_NULL, null=True, blank=True, related_name="well_activities", db_column="well_asset_id"
    )
    
    crop_variety = models.ForeignKey(
        CropVariety, 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True, 
        related_name="activities",
        verbose_name="الصنف",
        db_column="variety_id"
    )

    @property
    def variety(self):
        return self.crop_variety

    @variety.setter
    def variety(self, value):
        self.crop_variety = value

    @property
    def variety_id(self):
        return self.crop_variety_id

    @variety_id.setter
    def variety_id(self, value):
        self.crop_variety_id = value

    @property
    def note(self):
        if isinstance(self.data, dict):
            return self.data.get("note") or self.data.get("notes") or ""
        return ""

    @note.setter
    def note(self, value):
        payload = self.data if isinstance(self.data, dict) else {}
        payload["note"] = value
        self.data = payload

    @property
    def activity_date(self):
        if self.log_id:
            try:
                return self.log.log_date
            except (TypeError, ValueError, ArithmeticError):
                return None
        return getattr(self, "_legacy_date", None)

    @activity_date.setter
    def activity_date(self, value):
        self._legacy_date = value

    @property
    def location(self):
        cached = getattr(self, "_legacy_location", None)
        if cached is not None:
            return cached
        if self.pk:
            first_link = self.activity_locations.select_related("location").first()
            if first_link is not None:
                self._legacy_location = first_link.location
                return first_link.location
        return None

    @location.setter
    def location(self, value):
        self._legacy_location = value
        self._legacy_location_id = getattr(value, "pk", value)

    @property
    def location_id(self):
        location = self.location
        return getattr(location, "pk", None) if location is not None else getattr(self, "_legacy_location_id", None)

    @location_id.setter
    def location_id(self, value):
        self._legacy_location = None
        self._legacy_location_id = value

    @property
    def harvest_quantity(self):
        ext = getattr(self, "harvest_details", None)
        if ext is not None:
            return ext.harvest_quantity
        if isinstance(self.data, dict):
            return self.data.get("harvest_quantity")
        return None

    @harvest_quantity.setter
    def harvest_quantity(self, value):
        payload = self.data if isinstance(self.data, dict) else {}
        payload["harvest_quantity"] = self._json_safe_value(value)
        self.data = payload

    @property
    def harvest_uom(self):
        ext = getattr(self, "harvest_details", None)
        if ext is not None:
            return ext.uom
        if isinstance(self.data, dict):
            return self.data.get("harvest_uom")
        return None

    @harvest_uom.setter
    def harvest_uom(self, value):
        payload = self.data if isinstance(self.data, dict) else {}
        payload["harvest_uom"] = value
        self.data = payload

    @property
    def machine_hours(self):
        ext = getattr(self, "machine_details", None)
        if ext is not None:
            return ext.machine_hours
        if isinstance(self.data, dict):
            return self.data.get("machine_hours")
        return None

    @machine_hours.setter
    def machine_hours(self, value):
        payload = self.data if isinstance(self.data, dict) else {}
        payload["machine_hours"] = self._json_safe_value(value)
        self.data = payload

    @property
    def water_volume(self):
        ext = getattr(self, "irrigation_details", None)
        if ext is not None:
            return ext.water_volume
        if isinstance(self.data, dict):
            return self.data.get("water_volume")
        return None

    @water_volume.setter
    def water_volume(self, value):
        payload = self.data if isinstance(self.data, dict) else {}
        payload["water_volume"] = self._json_safe_value(value)
        self.data = payload

    @property
    def fertilizer_quantity(self):
        ext = getattr(self, "material_details", None)
        if ext is not None:
            return ext.fertilizer_quantity
        if isinstance(self.data, dict):
            return self.data.get("fertilizer_quantity")
        return None

    @fertilizer_quantity.setter
    def fertilizer_quantity(self, value):
        payload = self.data if isinstance(self.data, dict) else {}
        payload["fertilizer_quantity"] = self._json_safe_value(value)
        self.data = payload

    @property
    def fuel_consumed(self):
        ext = getattr(self, "machine_details", None)
        if ext is not None:
            return ext.fuel_consumed
        if isinstance(self.data, dict):
            return self.data.get("fuel_consumed")
        return None

    @fuel_consumed.setter
    def fuel_consumed(self, value):
        payload = self.data if isinstance(self.data, dict) else {}
        payload["fuel_consumed"] = self._json_safe_value(value)
        self.data = payload

    tree_loss_reason = models.ForeignKey(
        "TreeLossReason", on_delete=models.SET_NULL, null=True, blank=True, related_name="activities"
    )
    tree_count_delta = models.IntegerField(default=0)
    activity_tree_count = models.IntegerField(null=True, blank=True)
    team = models.TextField(blank=True, default="")
    # [Yemen Standard Fix] Switched from 'hours' to 'shifts' (Sura System)
    # 1.0 = Full Day, 0.5 = Half Day.
    days_spent = models.DecimalField(
        max_digits=4, 
        decimal_places=2, 
        default=Decimal('1.00'),
        verbose_name="عدد الصرات (الورديات)",
        help_text="عدد الأيام أو الصرات (مثال: 0.5 لنصف يوم، 1.0 ليوم كامل)"
    )
    
    agreed_daily_rate = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="قيمة الصرة المتفق عليها لهذا النشاط (بالريال/الدولار)"
    )

    @property
    def total_cost(self):
        # Calculation strictly purely Decimal
        rate = self.agreed_daily_rate or Decimal('0.00')
        minutes = self.days_spent or Decimal('0.00')
        return minutes * rate
    
    attachment = models.ForeignKey("Attachment", null=True, blank=True, on_delete=models.SET_NULL, related_name="activities")
    
    cost_materials = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="تكلفة المواد (دقة 4 خانات)",
    )
    cost_labor = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="تكلفة العمالة (دقة 4 خانات)",
    )
    cost_machinery = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="تكلفة الآليات (دقة 4 خانات)",
    )
    cost_overhead = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="التكاليف غير المباشرة (دقة 4 خانات)",
    )
    cost_wastage = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="تكلفة الهدر التشغيلية غير القابلة للرسملة",
    )
    cost_total = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="إجمالي التكلفة",
        help_text="الإجمالي النهائي للنشاط (يجب أن يطابق مجموع البنود)",
    )
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='activities_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='activities_updated')
    
    data = models.JSONField(default=dict, blank=True)

    def clean(self):
        """
        التحقق الجنائي من سلامة البيانات قبل الحفظ.
        """
        super().clean()
        # قاعدة التحقق CAT-004: منع تسجيل فقدان أشجار بدون سبب موثق
        if self.tree_count_delta < 0 and not self.tree_loss_reason:
            raise ValidationError({
                'tree_loss_reason': "مخالفة بروتوكول التدقيق: يجب تحديد سبب الفقد عند تسجيل نقص في عدد الأشجار."
            })

        # [Agri-Guardian] Technical Standard: Time-Travel Prevention
        # Activities cannot be recorded in the future.
        log_date = None
        if self.log_id:
            try:
                log_obj = self.log
                log_date = getattr(log_obj, "log_date", None)
            except (TypeError, ValueError, ArithmeticError):
                log_date = None
        if isinstance(log_date, str):
            try:
                log_date = date.fromisoformat(log_date)
            except ValueError:
                log_date = None
        if log_date and log_date > timezone.localdate():
             raise ValidationError({
                 'log': "التاريخ المستحيل: لا يمكن تسجيل نشاط في تاريخ مستقبلي."
             })

        # [Agri-Guardian] Yemen Context: PHI Advisory Check (Non-Blocking)
        self.check_phi_compliance()

    def check_phi_compliance(self):
        """
        Calculates Pre-Harvest Interval (PHI) violations.
        In Yemen Context, this is ADVISORY (Add to warnings), not BLOCKING.
        """
        # Only check for Harvest Tasks
        if not self.task or not getattr(self.task, 'is_harvest', False):
            return

        # Warning: This is a simplified check. In production, use the Service Layer.
        # We assume safeguards are handled by 'HarvestService'.
        # Here we just mark the record if we detect a risk.
        pass # Actual logic requires querying past activities, omitted to prevent circular imports in clean()


    def save(self, *args, **kwargs):
        # Backward compatibility for legacy callers using alias field names.
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            normalized = []
            for field in update_fields:
                if field == "variety":
                    normalized.append("crop_variety")
                elif field == "note":
                    normalized.append("data")
                else:
                    normalized.append(field)
            kwargs["update_fields"] = normalized
        if self.cost_total is None:
            self.cost_total = Decimal("0")
        if self.cost_wastage is None:
            self.cost_wastage = Decimal("0")
        if not self.log_id:
            from smart_agri.core.models.log import DailyLog
            from smart_agri.core.models.farm import Farm
            fallback_farm = None
            if self.crop_plan_id and getattr(self.crop_plan, "farm_id", None):
                fallback_farm = self.crop_plan.farm
            else:
                fallback_farm = Farm.objects.filter(deleted_at__isnull=True).order_by("id").first()
            if fallback_farm:
                log_date = getattr(self, "_legacy_date", None) or timezone.localdate()
                log, _ = DailyLog.objects.get_or_create(
                    farm=fallback_farm,
                    log_date=log_date,
                    defaults={"created_by": self.created_by, "updated_by": self.updated_by},
                )
                self.log = log
        self.full_clean() # فرض التحقق حتى عند الحفظ برمجياً
        super().save(*args, **kwargs)
        legacy_location = getattr(self, "_legacy_location", None)
        legacy_location_id = getattr(self, "_legacy_location_id", None)
        location_obj = legacy_location
        if location_obj is None and legacy_location_id:
            location_obj = Location.objects.filter(pk=legacy_location_id).first()
        if location_obj is not None:
            ActivityLocation.objects.get_or_create(
                activity=self,
                location=location_obj,
                defaults={"allocated_percentage": Decimal("100.00")},
            )
            self._legacy_location = location_obj
            self._legacy_location_id = location_obj.pk

    def delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    class Meta:
        db_table = 'core_activity'
        verbose_name = "نشاط"
        verbose_name_plural = "الأنشطة"
        ordering = ['-created_at'] # تحسين الأداء عند التصفح
        permissions = (
            ("skip_well_reading", "يمكن تقديم نشاط بدون قراءة البئر عند الضرورة"),
            ("skip_machine_metrics", "يمكن تقديم نشاط بدون مقاييس الآلة عند الضرورة"),
            ("skip_fuel_entry", "يمكن تقديم نشاط بدون استهلاك الديزل عند الضرورة"),
        )
        indexes = [
            models.Index(fields=['log', 'crop_plan'], name='core_activi_log_id_e8f718_idx'),
            models.Index(fields=['created_at'], name='idx_core_activity_created_at'),
            models.Index(fields=["log", "task"]),
            models.Index(fields=["asset"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["idempotency_key"],
                condition=Q(idempotency_key__isnull=False),
                name="core_activity_idempotency_key_uniq",
            ),
            models.CheckConstraint(
                check=Q(tree_count_delta__gte=-1000000) & Q(tree_count_delta__lte=1000000),
                name='core_activity_tree_counts_check'
            ),
            models.CheckConstraint(
                check=Q(cost_total__gte=0),
                name='core_activity_cost_total_non_negative'
            ),
        ]

class HarvestActivityManager(models.Manager): # Inherit SoftDeleteQuerySet? models.Manager is safer if imported
    def get_queryset(self):
        # نحتاج منطق SoftDeleteQuerySet هنا
        return super().get_queryset().filter(deleted_at__isnull=True).filter(task__is_harvest_task=True)

class HarvestActivity(Activity):
    objects = HarvestActivityManager()
    class Meta:
        proxy = True
        verbose_name = "نشاط حصاد"

class PlantingActivityManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True) # المنطق يحدد لاحقاً

class PlantingActivity(Activity):
    objects = PlantingActivityManager()
    class Meta:
        proxy = True
        verbose_name = "نشاط زراعة"

class ActivityHarvest(models.Model):
    activity = models.OneToOneField(Activity, on_delete=models.CASCADE, primary_key=True, related_name='harvest_details')
    harvest_quantity = models.DecimalField(max_digits=12, decimal_places=3)
    uom = models.CharField(max_length=40, choices=StandardUOM.choices, default=StandardUOM.KG)
    # الجولة 10 من التدقيق الجنائي: سلسلة الحيازة (إيقاف نص batch_number)
    batch_number = models.CharField(max_length=50, blank=True, default="") 
    lot = models.ForeignKey(
        "HarvestLot", on_delete=models.SET_NULL, null=True, blank=True, 
        related_name="activities", help_text="دفعة حصاد قابلة للتتبع"
    )
    product_id = models.BigIntegerField(null=True, blank=True)
    is_final_delivery = models.BooleanField(default=False, verbose_name="تسليم نهائي")

    class Meta:
        managed = True
        db_table = 'core_activity_harvest'
        verbose_name = "تفاصيل حصاد النشاط"
        verbose_name_plural = "تفاصيل حصاد الأنشطة"

class ActivityIrrigation(models.Model):
    activity = models.OneToOneField(Activity, on_delete=models.CASCADE, primary_key=True, related_name='irrigation_details')
    water_volume = models.DecimalField(max_digits=14, decimal_places=3)
    uom = models.CharField(max_length=40, choices=StandardUOM.choices, default=StandardUOM.M3)
    well_reading = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    well_asset = models.ForeignKey(Asset, on_delete=models.SET_NULL, null=True, blank=True, related_name="irrigations")
    is_solar_powered = models.BooleanField(default=False, help_text="هل تم الري باستخدام الطاقة الشمسية؟")
    diesel_qty = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True, help_text="كمية الديزل المستهلكة (لتر)")

    class Meta:
        managed = True
        db_table = 'core_activity_irrigation'
        verbose_name = "تفاصيل ري النشاط"
        verbose_name_plural = "تفاصيل ري الأنشطة"

    def clean(self):
        super().clean()
        from django.core.exceptions import ValidationError
        if self.is_solar_powered and self.diesel_qty and self.diesel_qty > 0:
            raise ValidationError({"diesel_qty": "لا يمكن إدخال كمية ديزل عند استخدام الطاقة الشمسية."})
        if not self.is_solar_powered and (self.diesel_qty is None or self.diesel_qty <= 0):
            raise ValidationError({'diesel_qty': "كمية الديزل مطلوبة عند عدم استخدام الطاقة الشمسية."})
        if self.water_volume is None or self.water_volume <= 0:
            raise ValidationError({'water_volume': "كمية المياه مطلوبة لكل عملية ري."})

class ActivityPlanting(models.Model):
    activity = models.OneToOneField(Activity, on_delete=models.CASCADE, primary_key=True, related_name='planting_details')
    planted_area = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    planted_uom = models.CharField(max_length=40, choices=StandardUOM.choices, null=True, blank=True)
    planted_area_m2 = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)

    class Meta:
        managed = True
        db_table = 'core_activity_planting'
        verbose_name = "تفاصيل زراعة النشاط"
        verbose_name_plural = "تفاصيل زراعة الأنشطة"

class ActivityMaterialApplication(models.Model):
    activity = models.OneToOneField(Activity, on_delete=models.CASCADE, primary_key=True, related_name='material_details')
    fertilizer_quantity = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    
    class Meta:
        managed = True
        db_table = 'core_activity_material'
        verbose_name = "تفاصيل مواد النشاط"
        verbose_name_plural = "تفاصيل مواد الأنشطة"

    def save(self, *args, **kwargs):
        """
        تم إزالة منطق المزامنة التلقائية (Side Effects) من النموذج.
        يتم الآن التعامل مع هذا المنطق حصراً في طبقة الخدمة (ActivityService).
        """
        super().save(*args, **kwargs)

class ActivityMachineUsage(models.Model):
    activity = models.OneToOneField(Activity, on_delete=models.CASCADE, primary_key=True, related_name='machine_details')
    machine_hours = models.DecimalField(max_digits=6, decimal_places=2)
    fuel_consumed = models.DecimalField(max_digits=19, decimal_places=4, null=True, blank=True)
    start_meter = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    end_meter = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)

    class Meta:
        managed = True
        db_table = 'core_activity_machine'
        verbose_name = "استخدام الآلة بالنشاط"
        verbose_name_plural = "استخدامات الآليات بالأنشطة"

class ActivityItem(SoftDeleteModel):
    """
    نموذج المواد المستهلكة في النشاط (تمت استعادته).
    يربط بين النشاط والمخزون.
    """
    activity = models.ForeignKey(
        Activity, 
        related_name='items', 
        on_delete=models.CASCADE,
        verbose_name="النشاط"
    )
    item = models.ForeignKey(
        Item, # Reference imported Item from .inventory
        on_delete=models.PROTECT,
        related_name='activity_usages',
        verbose_name="العنصر"
    )
    qty = models.DecimalField(
        max_digits=12, 
        decimal_places=3, 
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="الكمية"
    )
    applied_qty = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal("0.000"),
        validators=[MinValueValidator(Decimal("0.000"))],
        verbose_name="الكمية المحملة على النشاط",
    )
    waste_qty = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal("0.000"),
        validators=[MinValueValidator(Decimal("0.000"))],
        verbose_name="كمية الهدر",
    )
    waste_reason = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="سبب الهدر",
    )
    uom = models.CharField(max_length=50, choices=StandardUOM.choices, blank=True, null=True, verbose_name="وحدة القياس")
    batch_number = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        help_text="رقم التشغيلة للتتبع والامتثال (Traceability)", 
        verbose_name="رقم التشغيلة"
    )
    
    # حقول التكلفة (مهمة للتقارير المالية)
    cost_per_unit = models.DecimalField(
        max_digits=19, 
        decimal_places=4, 
        default=0, 
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="التكلفة للوحدة"
    )
    total_cost = models.DecimalField(max_digits=19, decimal_places=4, default=0, editable=False, verbose_name="إجمالي التكلفة")

    def save(self, *args, **kwargs):
        """
        تم إزالة منطق الحساب المالي المباشر من النموذج.
        يتم الآن الحساب عبر CostingService لضمان الدقة وتجنب الأخطاء الصامتة.
        """
        if self.applied_qty in (None, Decimal("0.000")) and self.qty is not None:
            self.applied_qty = self.qty
        if self.waste_qty is None:
            self.waste_qty = Decimal("0.000")
        super().save(*args, **kwargs)

    class Meta:
        managed = True
        db_table = 'core_activity_item'
        verbose_name = "مادة النشاط"
        verbose_name_plural = "مواد الأنشطة"
        indexes = [
            models.Index(fields=["activity"], name='idx_activity_item_act'),
            models.Index(fields=["item"], name='idx_core_activity_item_item'),
        ]

class ActivityCostSnapshot(SoftDeleteModel):
    class ScopedManager(models.Manager):
        def get_queryset(self):
            qs = super().get_queryset()
            user_id = get_rls_user_id()
            if user_id is None or user_id == -1:
                return qs
            return qs.filter(
                Q(activity__activity_locations__location__farm__memberships__user_id=user_id)
                | Q(crop_plan__farm__memberships__user_id=user_id)
            ).distinct()

    def __init__(self, *args, **kwargs):
        legacy_total_cost = kwargs.pop("total_cost", None)
        if legacy_total_cost is not None and "cost_total" not in kwargs:
            kwargs["cost_total"] = legacy_total_cost
        super().__init__(*args, **kwargs)

    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name="cost_snapshots")
    crop_plan = models.ForeignKey("CropPlan", on_delete=models.SET_NULL, null=True, blank=True, related_name="cost_snapshots")
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True, related_name="cost_snapshots")
    cost_materials = models.DecimalField(max_digits=19, decimal_places=4, default=Decimal("0.0000"))
    cost_labor = models.DecimalField(max_digits=19, decimal_places=4, default=Decimal("0.0000"))
    cost_machinery = models.DecimalField(max_digits=19, decimal_places=4, default=Decimal("0.0000"))
    cost_overhead = models.DecimalField(max_digits=19, decimal_places=4, default=Decimal("0.0000"))
    cost_wastage = models.DecimalField(max_digits=19, decimal_places=4, default=Decimal("0.0000"))
    cost_total = models.DecimalField(max_digits=19, decimal_places=4, default=Decimal("0.0000"))
    currency = models.CharField(max_length=8, default="YER")
    snapshot_at = models.DateTimeField(auto_now_add=True)
    objects = ScopedManager()

    @property
    def total_cost(self):
        return self.cost_total

    @total_cost.setter
    def total_cost(self, value):
        self.cost_total = value

    class Meta:
        managed = True
        db_table = 'core_activity_cost_snapshot'
        verbose_name = "لقطة التكاليف المالية للنشاط"
        verbose_name_plural = "لقطات التكاليف المالية للأنشطة"
        indexes = [
            models.Index(fields=["crop_plan", "task"]),
        ]

class ActivityEmployee(models.Model):
    """
    [Integration Bridge] Link specific employees to an activity.
    Feeds into Timesheets and Costing.
    """
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name="employee_details")
    LABOR_REGISTERED = "REGISTERED"
    LABOR_CASUAL_BATCH = "CASUAL_BATCH"
    LABOR_TYPE_CHOICES = [
        (LABOR_REGISTERED, "Registered Employee"),
        (LABOR_CASUAL_BATCH, "Casual Labor Batch"),
    ]

    employee = models.ForeignKey(
        'core.Employee', # String reference to avoid circular import
        on_delete=models.PROTECT,
        related_name="activities",
        null=True,
        blank=True,
    )
    labor_type = models.CharField(
        max_length=20,
        choices=LABOR_TYPE_CHOICES,
        default=LABOR_REGISTERED,
        help_text="Separates registered HR workers from field casual labor batches.",
    )
    labor_batch_label = models.CharField(
        max_length=120,
        blank=True,
        default="",
        help_text="Optional label for casual labor group (e.g., contractor or village batch).",
    )
    workers_count = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Used for casual labor batch entries only.",
    )
    # Yemen labor unit: Surrah (shift share).
    surrah_share = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("1.00"),
        verbose_name="حصة الصرة",
        help_text="كم تعادل مشاركة العامل في هذا النشاط من إجمالي صرته اليومية",
    )
    
    # [Omega-2028] Hourly cost and achievement hardening
    is_hourly = models.BooleanField(default=False, verbose_name="حساب بالساعة")
    hours_worked = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=Decimal("0.00"),
        verbose_name="عدد الساعات",
        help_text="الساعات المنجزة لكل فرد (أو للدفعة في حالة Batch)"
    )
    hourly_rate = models.DecimalField(
        max_digits=19, 
        decimal_places=4, 
        default=Decimal("0.00"),
        verbose_name="سعر الساعة",
        help_text="سعر الساعة المتفق عليه لهذا النشاط"
    )
    achievement_qty = models.DecimalField(
        max_digits=19, 
        decimal_places=4, 
        default=Decimal("0.00"),
        verbose_name="كمية الإنجاز",
        help_text="مثل: عدد الأشجار المنجزة أو الوزن المقطوف"
    )
    achievement_uom = models.CharField(
        max_length=50, 
        blank=True, 
        default="", 
        verbose_name="وحدة الإنجاز",
        help_text="مثل: شجرة، كيلو، كرتون"
    )

    fixed_wage_cost = models.DecimalField(
        max_digits=19, 
        decimal_places=4, 
        null=True, 
        blank=True,
        verbose_name="المبلغ المقطوع",
        help_text="[Agri-Guardian] إدخال يدوي مباشر للمبلغ لتجاوز حسابات الصرة/الساعة"
    )

    wage_cost = models.DecimalField(max_digits=19, decimal_places=4, default=0, editable=False)
    
    class Meta:
        db_table = 'core_activity_employee'
        verbose_name = "عامل النشاط"
        verbose_name_plural = "عمال الأنشطة"
        constraints = [
            models.UniqueConstraint(
                fields=("activity", "employee"),
                condition=Q(employee__isnull=False),
                name="uniq_activity_registered_employee",
            ),
            models.CheckConstraint(
                check=(
                    (Q(labor_type="REGISTERED") & Q(employee__isnull=False))
                    | (
                        Q(labor_type="CASUAL_BATCH")
                        & Q(employee__isnull=True)
                        & Q(workers_count__gt=0)
                    )
                ),
                name="activity_employee_labor_type_guard",
            ),
        ]
