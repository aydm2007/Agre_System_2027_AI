from datetime import date
from decimal import Decimal
from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.utils import timezone
from .base import SoftDeleteModel
from .farm import Farm, Asset

class Supervisor(SoftDeleteModel):
    def __init__(self, *args, **kwargs):
        legacy_user = kwargs.pop("user", None)
        if legacy_user is not None:
            kwargs.setdefault("name", getattr(legacy_user, "username", str(legacy_user)))
            kwargs.setdefault("code", f"USR-{getattr(legacy_user, 'id', 'legacy')}")
        super().__init__(*args, **kwargs)

    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="supervisors")
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.farm.name} - {self.name}"

    class Meta:
        verbose_name = "مشرف"
        verbose_name_plural = "المشرفين"
        constraints = [
             models.UniqueConstraint(
                fields=['code'],
                condition=Q(deleted_at__isnull=True),
                name='unique_supervisor_code_active'
            ),
        ]

class LaborRate(SoftDeleteModel):
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="labor_rates")
    role_name = models.CharField(max_length=100, default="عامل يومي")
    daily_rate = models.DecimalField(max_digits=19, decimal_places=4, null=True, blank=True)
    cost_per_hour = models.DecimalField(max_digits=19, decimal_places=4)
    currency = models.CharField(max_length=8, default="YER")
    effective_date = models.DateField(default=timezone.now)

    class Meta:
        managed = True
        db_table = 'core_laborrate'
        unique_together = ("farm", "role_name", "effective_date")
        ordering = ["farm", "role_name", "-effective_date"]

    def clean(self):
        super().clean()
        if self.pk is None and self.daily_rate is None:
            raise ValidationError("ERR_DAILY_RATE_REQUIRED")

    def __str__(self):
        if self.daily_rate is not None:
            return f"{self.farm.name} / {self.role_name} - {self.daily_rate} {self.currency}/day"
        return f"{self.farm.name} / {self.role_name} - {self.cost_per_hour} {self.currency}/hr"

class MachineRate(SoftDeleteModel):
    asset = models.OneToOneField(Asset, on_delete=models.CASCADE, related_name="machine_rate")
    daily_rate = models.DecimalField(max_digits=19, decimal_places=4, null=True, blank=True)
    cost_per_hour = models.DecimalField(max_digits=19, decimal_places=4)
    fuel_consumption_rate = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="لتر/ساعة",
    )
    currency = models.CharField(max_length=8, default="YER")

    class Meta:
        managed = True
        db_table = 'core_machinerate'

    def clean(self):
        super().clean()
        if self.pk is None and self.daily_rate is None:
            raise ValidationError("ERR_MACHINE_DAILY_RATE_REQUIRED")

    def __str__(self):
        if self.daily_rate is not None:
            return f"{self.asset.name} - {self.daily_rate} {self.currency}/day"
        return f"{self.asset.name} - {self.cost_per_hour} {self.currency}/hr"



class Uom(models.Model):
    """
    Base Unit of Measure (UOM) reference table.
    
    MANAGED=True Rationale:
    - This is a SYSTEM-WIDE reference table.
    - We enforce schema control via Django Migrations to ensure consistency.
    - UOM codes (kg, L, m3, etc.) must be consistent across all integrated systems.
    - Table 'core_uom' is maintained by SQL scripts synced with external systems.
    - Changes require coordination with ERP team to avoid ID/code mismatches.
    - For application-specific unit mappings, use the Unit model instead.
    """
    code = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20)
    is_base = models.BooleanField(default=False)
    to_base_factor = models.DecimalField(max_digits=18, decimal_places=6, default=1)
    decimals = models.PositiveSmallIntegerField(default=3)

    class Meta:
        managed = True
        db_table = 'core_uom'
        verbose_name = "Unit of Measure (Base)"
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class SystemSettings(models.Model):
    """
    نموذج إعدادات النظام المركزي (Singleton Pattern).
    يتحكم في تفعيل أو تعطيل القيود المحاسبية الصارمة (Hybrid ERP Toggle).

    - strict_erp_mode=False (Default / Shadow Mode):
      المزارع يدخل البيانات بحرية، والنظام يسجل أي تجاوز مالي كتنبيه رقابي صامت (VarianceAlert)
      ليتم التحقيق فيه لاحقاً دون إعاقة العمل الميداني.

    - strict_erp_mode=True (Strict ERP Mode):
      النظام يمنع حفظ أي عملية تتجاوز الميزانية المعتمدة — يتطلب تعزيز مالي مسبق من القطاع.
    """
    strict_erp_mode = models.BooleanField(
        default=False,
        help_text=(
            "True = يمنع الحفظ عند تجاوز الميزانية (Hard Block). "
            "False = يحفظ ويصدر تنبيه للإدارة (Shadow Mode)."
        ),
    )

    allowed_variance_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('10.00'),
        help_text="نسبة الانحراف المسموح بها قبل إصدار إنذار (مثال: 10.00 تعني 10%).",
    )

    # [AGRI-GUARDIAN Axis 8] Expense auto-approval ceiling (YER)
    expense_auto_approve_limit = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        default=Decimal('5000.00'),
        help_text="الحد الأقصى للمصروفات التي تُعتمد تلقائياً بدون مراجعة (ر.ي). ما فوقها يحتاج موافقة.",
    )

    # Diesel dipstick tolerance (%)
    diesel_tolerance_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('5.00'),
        help_text="هامش التسامح المسموح للديزل (مثال: 5.00 تعني 5% فوق الاستهلاك المعياري).",
    )

    # Audit trail
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        'auth.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        help_text="آخر من قام بتعديل هذه الإعدادات الحساسة.",
    )

    def save(self, *args, **kwargs):
        """
        Singleton enforcement: prevent creating a second row.
        Only the row with pk=1 is allowed. If a row already exists
        and this is a new insert, block it.
        """
        if not self.pk and SystemSettings.objects.exists():
            raise ValidationError(
                "🔴 [FORENSIC BLOCK] المعمارية تمنع إنشاء أكثر من سجل إعدادات واحد "
                "للنظام (Singleton). استخدم SystemSettings.get_settings() للتحديث."
            )
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Block deletion — SystemSettings must always exist."""
        raise ValidationError(
            "🔴 [FORENSIC BLOCK] لا يمكن حذف السجل المركزي لإعدادات النظام."
        )

    @classmethod
    def get_settings(cls):
        """
        Safe accessor: returns the singleton row, creating it with
        defaults if it doesn't exist yet (first deployment scenario).
        """
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj

    class Meta:
        managed = True
        db_table = 'core_systemsettings'
        verbose_name = "إعدادات النظام المركزية"
        verbose_name_plural = "إعدادات النظام المركزية"

    def __str__(self):
        mode = "صارم (Strict)" if self.strict_erp_mode else "مرن / ظل (Shadow)"
        return f"إعدادات النظام — الوضع: {mode}"


class RemoteReviewLog(models.Model):
    REVIEW_TYPE_WEEKLY = "weekly"
    REVIEW_TYPE_EXCEPTION = "exception"
    REVIEW_TYPE_CHOICES = [
        (REVIEW_TYPE_WEEKLY, "مراجعة أسبوعية"),
        (REVIEW_TYPE_EXCEPTION, "مراجعة استثنائية"),
    ]

    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="remote_review_logs")
    reviewed_by = models.ForeignKey('auth.User', on_delete=models.PROTECT, related_name='remote_reviews')
    reviewed_at = models.DateTimeField(auto_now_add=True)
    review_type = models.CharField(max_length=20, choices=REVIEW_TYPE_CHOICES, default=REVIEW_TYPE_WEEKLY)
    notes = models.TextField(blank=True, default="")
    exceptions_found = models.PositiveIntegerField(default=0)

    class Meta:
        managed = True
        db_table = 'core_remotereviewlog'
        verbose_name = "سجل المراجعة القطاعية عن بعد"
        verbose_name_plural = "سجلات المراجعة القطاعية عن بعد"
        ordering = ['-reviewed_at']

    def __str__(self):
        return f"{self.farm.name} @ {self.reviewed_at:%Y-%m-%d}"




class RemoteReviewEscalation(models.Model):
    LEVEL_DUE = "due"
    LEVEL_OVERDUE = "overdue"
    LEVEL_BLOCKED = "blocked"
    LEVEL_CHOICES = [
        (LEVEL_DUE, "مستحق"),
        (LEVEL_OVERDUE, "متأخر"),
        (LEVEL_BLOCKED, "محجوب"),
    ]

    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="remote_review_escalations")
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default=LEVEL_DUE)
    reason = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        managed = True
        db_table = 'core_remotereviewescalation'
        verbose_name = "تصعيد مراجعة قطاعية عن بعد"
        verbose_name_plural = "تصعيدات المراجعة القطاعية عن بعد"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.farm.name} / {self.level} @ {self.created_at:%Y-%m-%d}"


class FarmSettings(models.Model):
    """
    [AGRI-GUARDIAN Axis 15] Dual-Mode ERP per tenant.
    Controls SIMPLE (technical view) vs STRICT (ERP view) modes,
    along with specific modular toggles like Zakat and Depreciation.
    """
    MODE_SIMPLE = 'SIMPLE'
    MODE_STRICT = 'STRICT'
    MODE_CHOICES = [
        (MODE_SIMPLE, 'مبسط (فني/رقابي)'),
        (MODE_STRICT, 'صارم (ERP متكامل)'),
    ]

    VARIANCE_BEHAVIOR_WARN = 'warn'
    VARIANCE_BEHAVIOR_BLOCK = 'block'
    VARIANCE_BEHAVIOR_QUARANTINE = 'quarantine'
    VARIANCE_BEHAVIOR_CHOICES = [
        (VARIANCE_BEHAVIOR_WARN, 'تنبيه فقط'),
        (VARIANCE_BEHAVIOR_BLOCK, 'منع التنفيذ'),
        (VARIANCE_BEHAVIOR_QUARANTINE, 'حجر ومراجعة'),
    ]

    COST_VISIBILITY_RATIOS_ONLY = 'ratios_only'
    COST_VISIBILITY_SUMMARIZED = 'summarized_amounts'
    COST_VISIBILITY_FULL = 'full_amounts'
    COST_VISIBILITY_CHOICES = [
        (COST_VISIBILITY_RATIOS_ONLY, 'نسب فقط'),
        (COST_VISIBILITY_SUMMARIZED, 'مبالغ ملخصة'),
        (COST_VISIBILITY_FULL, 'مبالغ كاملة'),
    ]

    APPROVAL_PROFILE_BASIC = 'basic'
    APPROVAL_PROFILE_TIERED = 'tiered'
    APPROVAL_PROFILE_STRICT_FINANCE = 'strict_finance'
    APPROVAL_PROFILE_CHOICES = [
        (APPROVAL_PROFILE_BASIC, 'أساسي'),
        (APPROVAL_PROFILE_TIERED, 'حسب شريحة المزرعة'),
        (APPROVAL_PROFILE_STRICT_FINANCE, 'مالي صارم'),
    ]

    CONTRACT_MODE_DISABLED = 'disabled'
    CONTRACT_MODE_OPERATIONAL_ONLY = 'operational_only'
    CONTRACT_MODE_FULL_ERP = 'full_erp'
    CONTRACT_MODE_CHOICES = [
        (CONTRACT_MODE_DISABLED, 'معطل'),
        (CONTRACT_MODE_OPERATIONAL_ONLY, 'تشغيلي فقط'),
        (CONTRACT_MODE_FULL_ERP, 'ERP كامل'),
    ]

    TREASURY_VISIBILITY_HIDDEN = 'hidden'
    TREASURY_VISIBILITY_FINANCE_ONLY = 'finance_only'
    TREASURY_VISIBILITY_VISIBLE = 'visible'
    TREASURY_VISIBILITY_CHOICES = [
        (TREASURY_VISIBILITY_HIDDEN, 'مخفي'),
        (TREASURY_VISIBILITY_FINANCE_ONLY, 'للفرق المالية فقط'),
        (TREASURY_VISIBILITY_VISIBLE, 'ظاهر'),
    ]

    FIXED_ASSET_MODE_TRACKING_ONLY = 'tracking_only'
    FIXED_ASSET_MODE_FULL_CAPITALIZATION = 'full_capitalization'
    FIXED_ASSET_MODE_CHOICES = [
        (FIXED_ASSET_MODE_TRACKING_ONLY, 'تتبع فقط'),
        (FIXED_ASSET_MODE_FULL_CAPITALIZATION, 'رسملة كاملة'),
    ]

    SHARECROPPING_MODE_FINANCIAL = 'FINANCIAL'
    SHARECROPPING_MODE_PHYSICAL = 'PHYSICAL'
    SHARECROPPING_MODE_CHOICES = [
        (SHARECROPPING_MODE_FINANCIAL, 'مالية (نسبة من الإيرادات/الأرباح)'),
        (SHARECROPPING_MODE_PHYSICAL, 'عينية (نسبة من المحصول الفعلي)'),
    ]

    IRRIGATION_POWER_DIESEL = 'diesel'
    IRRIGATION_POWER_SOLAR = 'solar'
    IRRIGATION_POWER_CHOICES = [
        (IRRIGATION_POWER_DIESEL, 'ديزل'),
        (IRRIGATION_POWER_SOLAR, 'طاقة شمسية'),
    ]

    farm = models.OneToOneField(Farm, on_delete=models.CASCADE, related_name='settings')
    mode = models.CharField(
        max_length=20, 
        choices=MODE_CHOICES, 
        default=MODE_SIMPLE,
        help_text="تحديد النمط التشغيلي للمزرعة."
    )
    enable_zakat = models.BooleanField(
        default=True,
        help_text="تفعيل استقطاع الزكاة آلياً على المحاصيل."
    )
    enable_depreciation = models.BooleanField(
        default=True,
        help_text="تفعيل قيود الإهلاك الآلي المشتركة كـ (الطاقة الشمسية)."
    )
    # compatibility-only, display-only, not authoring authority in SIMPLE.
    show_finance_in_simple = models.BooleanField(
        default=False,
        help_text="خيار compatibility-only وdisplay-only في SIMPLE، وليس not authoring authority لمسارات المالية أو صلاحيات التعديل."
    )
    show_stock_in_simple = models.BooleanField(
        default=False,
        help_text="خيار compatibility-only وdisplay-only في SIMPLE، وليس not authoring authority لمسارات المخزون أو الكتابات الحاكمة."
    )
    show_employees_in_simple = models.BooleanField(
        default=False,
        help_text="خيار compatibility-only وdisplay-only في SIMPLE، وليس not authoring authority لمسارات الموظفين أو الرواتب أو صلاحيات authoring."
    )
    show_advanced_reports = models.BooleanField(
        default=False,
        help_text="إظهار التقارير المتقدمة في الواجهة المبسطة (Simple Mode)."
    )
    enable_sharecropping = models.BooleanField(
        default=False,
        help_text="تفعيل موديول الشراك وتقسيم حصص المحصول مع الشركاء."
    )
    sharecropping_mode = models.CharField(
        max_length=20,
        choices=SHARECROPPING_MODE_CHOICES,
        default=SHARECROPPING_MODE_FINANCIAL,
        help_text="طبيعة نسبة الشراكة: هل هي مالية أم عينية من كمية الحصاد؟"
    )
    enable_petty_cash = models.BooleanField(
        default=True,
        help_text="تفعيل دورة العهد النقدية (طلبات العهد وتسويتها)."
    )
    enabled_modules = models.JSONField(
        default=dict, 
        blank=True,
        help_text="الموديلات المفعلة لهذه المزرعة."
    )
    is_smart = models.BooleanField(
        default=False,
        help_text="هل المزرعة تدعم التقنيات الذكية؟"
    )
    is_rukun_locked = models.BooleanField(
        default=False,
        help_text="هل تم قفل المزرعة سيادياً (Rukun Locked)؟"
    )
    variance_behavior = models.CharField(
        max_length=20,
        choices=VARIANCE_BEHAVIOR_CHOICES,
        default=VARIANCE_BEHAVIOR_WARN,
        help_text="كيفية التعامل مع الانحرافات التشغيلية والمالية حسب سياسة المزرعة.",
    )
    cost_visibility = models.CharField(
        max_length=24,
        choices=COST_VISIBILITY_CHOICES,
        default=COST_VISIBILITY_SUMMARIZED,
        help_text="درجة إظهار التكلفة للمستخدمين في الواجهات التشغيلية.",
    )
    approval_profile = models.CharField(
        max_length=24,
        choices=APPROVAL_PROFILE_CHOICES,
        default=APPROVAL_PROFILE_TIERED,
        help_text="ملف الموافقات المعتمد لهذه المزرعة.",
    )
    contract_mode = models.CharField(
        max_length=24,
        choices=CONTRACT_MODE_CHOICES,
        default=CONTRACT_MODE_OPERATIONAL_ONLY,
        help_text="مستوى تفعيل العقود الزراعية والاستثمارية.",
    )
    treasury_visibility = models.CharField(
        max_length=24,
        choices=TREASURY_VISIBILITY_CHOICES,
        default=TREASURY_VISIBILITY_HIDDEN,
        help_text="سياسة إظهار الخزينة والمقبوضات حسب المود والصلاحيات.",
    )
    fixed_asset_mode = models.CharField(
        max_length=24,
        choices=FIXED_ASSET_MODE_CHOICES,
        default=FIXED_ASSET_MODE_TRACKING_ONLY,
        help_text="مدى تفعيل دورة الأصل الثابت: تتبع فقط أو رسملة كاملة.",
    )
    procurement_committee_threshold = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        default=Decimal('500000.0000'),
        help_text="الحد الأدنى لقيمة المشتريات التي تستلزم موافقة لجان."
    )
    remote_site = models.BooleanField(
        default=False,
        help_text="هل المزرعة بعيدة/صعبة الوصول بحيث تحتاج ضوابط تعويضية عن الحضور الميداني؟",
    )
    single_finance_officer_allowed = models.BooleanField(
        default=False,
        help_text="للمزارع الصغرى فقط: السماح بأن يقوم شخص مالي واحد محلياً بدور محاسب/رئيس حسابات/قائم بأعمال المدير المالي.",
    )
    local_finance_threshold = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        default=Decimal('100000.0000'),
        help_text="السقف المحلي الذي يمكن اعتماده داخل المزرعة قبل التصعيد إلى القطاع.",
    )
    sector_review_threshold = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        default=Decimal('250000.0000'),
        help_text="السقف الذي بعده تدخل مراجعة القطاع إلزامياً قبل الاعتماد النهائي.",
    )
    mandatory_attachment_for_cash = models.BooleanField(
        default=True,
        help_text="إلزام إرفاق مستندات للعمليات النقدية في المود الصارم.",
    )
    
    # --- Currency Settings --- #
    enable_multi_currency = models.BooleanField(
        default=False,
        help_text="تفعيل تعدد العملات (إذا كان معطلاً سيتم إجبار العملة الافتراضية)."
    )
    default_currency = models.CharField(
        max_length=8,
        default="YER",
        help_text="العملة الافتراضية للمزرعة."
    )
    
    weekly_remote_review_required = models.BooleanField(
        default=False,
        help_text="للمزارع البعيدة: إلزام مراجعة قطاعية أسبوعية عن بعد.",
    )
    attachment_transient_ttl_days = models.PositiveIntegerField(
        default=30,
        help_text="عمر النسخ المؤقتة/المسودات من المرفقات قبل purge أو archival.",
    )
    approved_attachment_archive_after_days = models.PositiveIntegerField(
        default=7,
        help_text="بعد كم يوم من الاعتماد النهائي تُنقل النسخة الحاكمة إلى طبقة أرشيفية منخفضة الكلفة.",
    )
    attachment_max_upload_size_mb = models.PositiveIntegerField(
        default=10,
        help_text="أقصى حجم رفع للمرفقات بالميجابايت حسب سياسة المزرعة.",
    )
    ATTACHMENT_SCAN_MODE_HEURISTIC = 'heuristic'
    ATTACHMENT_SCAN_MODE_CLAMAV = 'clamav'
    ATTACHMENT_SCAN_MODE_CHOICES = [
        (ATTACHMENT_SCAN_MODE_HEURISTIC, 'فحص هيوريستي'),
        (ATTACHMENT_SCAN_MODE_CLAMAV, 'ClamAV / خارجي'),
    ]
    attachment_scan_mode = models.CharField(
        max_length=24,
        choices=ATTACHMENT_SCAN_MODE_CHOICES,
        default=ATTACHMENT_SCAN_MODE_HEURISTIC,
        help_text="محرك فحص المرفقات المطلوب لهذه المزرعة.",
    )
    attachment_require_clean_scan_for_strict = models.BooleanField(
        default=True,
        help_text="منع مرور مرفق STRICT إذا لم يحصل على نتيجة فحص نظيفة.",
    )
    attachment_enable_cdr = models.BooleanField(
        default=False,
        help_text="تشغيل مسار إعادة بناء المحتوى CDR للمرفقات الحساسة عند توفره تشغيلياً.",
    )
    
    # --- Governance & Integrity: Multi-Location Toggles --- #
    allow_overlapping_crop_plans = models.BooleanField(
        default=False,
        help_text="السماح بإنشاء خطط زراعية متعددة لنفس المحصول في نفس الموسم (تجاوز قيد الازدواجية)."
    )
    allow_multi_location_activities = models.BooleanField(
        default=True,
        help_text="السماح باختيار مواقع متعددة دفعة واحدة عند تسجيل الأنشطة اليومية."
    )
    allow_cross_plan_activities = models.BooleanField(
        default=False,
        help_text="السماح بنشاط واحد يغطي مواقع تتبع أكثر من خطة زراعية مختلفة (مشاركة التكاليف المعقدة)."
    )
    allow_creator_self_variance_approval = models.BooleanField(
        default=False,
        help_text="السماح استثنائيًا لمنشئ اليومية باعتماد الانحراف الحرج لنفسه فقط وفق سياسة المزرعة، دون السماح باعتماد السجل النهائي.",
    )
    show_daily_log_smart_card = models.BooleanField(
        default=True,
        help_text="إظهار طبقة الكرت الذكي/السياق الذكي في اليومية عندما تفرضها المهمة والسياسة.",
    )
    show_operational_alerts = models.BooleanField(
        default=True,
        help_text="عرض التنبيهات التشغيلية وصحة النظام في لوحة المعلومات."
    )
    enable_timed_plan_compliance = models.BooleanField(
        default=False,
        help_text="تفعيل التحقق من الجدول الزمني (تسلسل المهام) لكل محصول."
    )
    sales_tax_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="نسبة ضريبة المبيعات المطبقة للمزرعة (مثلاً 15.00 لضريبة 15%)."
    )
    
    # --- Offline Retention Policy --- #
    offline_cache_retention_days = models.PositiveIntegerField(
        default=7,
        help_text="عدد أيام الاحتفاظ بكاش البحث (Lookup Cache) قبل الحذف التلقائي."
    )
    synced_draft_retention_days = models.PositiveIntegerField(
        default=3,
        help_text="عدد أيام الاحتفاظ بمسودات اليوميات المرفوعة بنجاح قبل الحذف."
    )
    dead_letter_retention_days = models.PositiveIntegerField(
        default=14,
        help_text="عدد أيام الاحتفاظ بالطلبات الفاشلة (Dead Letter) قبل الحذف النهائي."
    )
    
    # --- Perennial Trees Enhancements (Phase 10) --- #
    enable_tree_gis_zoning = models.BooleanField(
        default=False,
        help_text="تفعيل شاشة المراقبة المكانية المرئية (Tree GIS Heatmap) לגرد الأشجار."
    )
    enable_bulk_cohort_transition = models.BooleanField(
        default=False,
        help_text="تفعيل ميزة النقل المجمع للقطعان الجينية من مرحلة النمو للإنتاج."
    )
    enable_biocost_depreciation_predictor = models.BooleanField(
        default=False,
        help_text="تفعيل خوارزمية توقع الإهلاك المالي في الدفعات الشجرية."
    )
    
    enable_offline_media_purge = models.BooleanField(
        default=False,
        help_text="تفعيل المسح التلقائي للمرفقات (Media Purge) بعد المزامنة."
    )
    enable_offline_conflict_resolution = models.BooleanField(
        default=False,
        help_text="تفعيل واجهة حل النزاعات اللحظية عند وجود تضارب في البيانات."
    )
    enable_predictive_alerts = models.BooleanField(
        default=False,
        help_text="تفعيل التنبيهات الاستباقية للانحرافات الزمنية قبل وقوعها."
    )
    enable_local_purge_audit = models.BooleanField(
        default=False,
        help_text="تفعيل سجل التنظيف المحلي (Audit Log) لعمليات المسح."
    )
    
    enable_pos_barcode = models.BooleanField(
        default=False,
        help_text="تفعيل خيار المسح الضوئي (Barcode) في واجهة نقاط البيع."
    )
    default_irrigation_power_source = models.CharField(
        max_length=20,
        choices=IRRIGATION_POWER_CHOICES,
        default=IRRIGATION_POWER_DIESEL,
        help_text="المصدر الافتراضي لضخ المياه في الري (لتسهيل إدخال البيانات)",
    )

    POLICY_FIELD_CATALOG = {
        "mode": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "dual_mode_policy"},
        "variance_behavior": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "dual_mode_policy"},
        "cost_visibility": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "dual_mode_policy"},
        "approval_profile": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "dual_mode_policy"},
        "contract_mode": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "dual_mode_policy"},
        "treasury_visibility": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "dual_mode_policy"},
        "fixed_asset_mode": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "dual_mode_policy"},
        "show_daily_log_smart_card": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "dual_mode_policy"},
        "show_operational_alerts": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "dual_mode_policy"},
        "procurement_committee_threshold": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "finance_threshold_policy"},
        "single_finance_officer_allowed": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "finance_threshold_policy"},
        "local_finance_threshold": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "finance_threshold_policy"},
        "sector_review_threshold": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "finance_threshold_policy"},
        "sales_tax_percentage": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "finance_threshold_policy"},
        "enable_multi_currency": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "finance_threshold_policy"},
        "default_currency": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "finance_threshold_policy"},
        "mandatory_attachment_for_cash": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "attachment_policy"},
        "attachment_transient_ttl_days": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "attachment_policy"},
        "approved_attachment_archive_after_days": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "attachment_policy"},
        "attachment_max_upload_size_mb": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "attachment_policy"},
        "attachment_scan_mode": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "attachment_policy"},
        "attachment_require_clean_scan_for_strict": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "attachment_policy"},
        "attachment_enable_cdr": {"scope": "farm-readable", "edit_scope": "system-only", "section": "attachment_policy"},
        "enable_sharecropping": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "contract_policy"},
        "sharecropping_mode": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "contract_policy"},
        "enable_petty_cash": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "contract_policy"},
        "enable_zakat": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "agronomy_execution_policy"},
        "enable_depreciation": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "agronomy_execution_policy"},
        "allow_overlapping_crop_plans": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "agronomy_execution_policy"},
        "allow_multi_location_activities": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "agronomy_execution_policy"},
        "allow_cross_plan_activities": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "agronomy_execution_policy"},
        "allow_creator_self_variance_approval": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "agronomy_execution_policy"},
        "remote_site": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "remote_review_policy"},
        "weekly_remote_review_required": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "remote_review_policy"},
        "enable_tree_gis_zoning": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "agronomy_execution_policy"},
        "enable_bulk_cohort_transition": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "agronomy_execution_policy"},
        "enable_biocost_depreciation_predictor": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "agronomy_execution_policy"},
        "default_irrigation_power_source": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "agronomy_execution_policy"},
        "enable_timed_plan_compliance": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "agronomy_execution_policy"},
        "offline_cache_retention_days": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "offline_sync_policy"},
        "synced_draft_retention_days": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "offline_sync_policy"},
        "dead_letter_retention_days": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "offline_sync_policy"},
        "enable_offline_media_purge": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "offline_sync_policy"},
        "enable_offline_conflict_resolution": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "offline_sync_policy"},
        "enable_predictive_alerts": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "offline_sync_policy"},
        "enable_local_purge_audit": {"scope": "farm-readable", "edit_scope": "sector-editable", "section": "offline_sync_policy"},
        "enable_pos_barcode": {"scope": "farm-readable", "edit_scope": "farm-editable", "section": "dual_mode_policy"},
    }

    class Meta:
        managed = True
        db_table = 'core_farmsettings'
        verbose_name = "إعدادات المزرعة/السياسات المرنة"
        verbose_name_plural = "إعدادات المزارع/السياسات المرنة"

    def clean(self):
        super().clean()
        from smart_agri.accounts.models import FarmMembership
        from smart_agri.finance.services.farm_finance_authority_service import FarmFinanceAuthorityService

        if self.mode == self.MODE_STRICT and getattr(self.farm, 'tier', Farm.TIER_SMALL) in [Farm.TIER_MEDIUM, Farm.TIER_LARGE]:
            has_ffm = FarmMembership.objects.filter(
                farm_id=self.farm_id,
                role__in=FarmFinanceAuthorityService.FARM_FINANCE_MANAGER_ROLES
            ).exists()
            if not has_ffm:
                raise ValidationError(
                    "🔴 [GOVERNANCE BLOCK] المزارع من الفئة (متوسط/كبير) في المود الصارم تُلزم بوجود 'مدير مالي للمزرعة'."
                )

    def __str__(self):
        return f"إعدادات: {self.farm.name}"

    @property
    def mode_label(self):
        return "نظام ERP كامل (Strict)" if self.mode == self.MODE_STRICT else "نظام مبسط (Shadow)"

    @property
    def visibility_level(self):
        return "full_erp" if self.mode == self.MODE_STRICT else "operations_only"

    @classmethod
    def policy_field_catalog(cls):
        catalog = {}
        for field_name, meta in cls.POLICY_FIELD_CATALOG.items():
            field = cls._meta.get_field(field_name)
            if getattr(field, "choices", None):
                options = [{"value": value, "label": label} for value, label in field.choices]
            else:
                options = []
            field_type = field.get_internal_type()
            if field_type in {"BooleanField", "NullBooleanField"}:
                ui_type = "boolean"
            elif field_type in {"DecimalField", "FloatField"}:
                ui_type = "decimal"
            elif field_type in {"PositiveIntegerField", "IntegerField", "BigIntegerField"}:
                ui_type = "integer"
            elif options:
                ui_type = "choice"
            else:
                ui_type = "string"
            catalog[field_name] = {
                **meta,
                "label": getattr(field, "verbose_name", field_name).replace("_", " "),
                "help_text": getattr(field, "help_text", ""),
                "ui_type": ui_type,
                "options": options,
            }
        return catalog

    def policy_snapshot(self):
        return {
            "mode": self.mode,
            "mode_label": self.mode_label,
            "visibility_level": self.visibility_level,
            "variance_behavior": self.variance_behavior,
            "cost_visibility": self.cost_visibility,
            "approval_profile": self.approval_profile,
            "contract_mode": self.contract_mode,
            "treasury_visibility": self.treasury_visibility,
            "fixed_asset_mode": self.fixed_asset_mode,
            "procurement_committee_threshold": self.procurement_committee_threshold,
            "single_finance_officer_allowed": self.single_finance_officer_allowed,
            "local_finance_threshold": self.local_finance_threshold,
            "sector_review_threshold": self.sector_review_threshold,
            "sales_tax_percentage": self.sales_tax_percentage,
            "enable_multi_currency": self.enable_multi_currency,
            "default_currency": self.default_currency,
            "enable_zakat": self.enable_zakat,
            "enable_depreciation": self.enable_depreciation,
            "enable_sharecropping": self.enable_sharecropping,
            "enable_petty_cash": self.enable_petty_cash,
            "sharecropping_mode": self.sharecropping_mode,
            "mandatory_attachment_for_cash": self.mandatory_attachment_for_cash,
            "attachment_transient_ttl_days": self.attachment_transient_ttl_days,
            "approved_attachment_archive_after_days": self.approved_attachment_archive_after_days,
            "attachment_max_upload_size_mb": self.attachment_max_upload_size_mb,
            "attachment_scan_mode": self.attachment_scan_mode,
            "attachment_require_clean_scan_for_strict": self.attachment_require_clean_scan_for_strict,
            "attachment_enable_cdr": self.attachment_enable_cdr,
            "remote_site": self.remote_site,
            "weekly_remote_review_required": self.weekly_remote_review_required,
            "allow_overlapping_crop_plans": self.allow_overlapping_crop_plans,
            "allow_multi_location_activities": self.allow_multi_location_activities,
            "allow_cross_plan_activities": self.allow_cross_plan_activities,
            "allow_creator_self_variance_approval": self.allow_creator_self_variance_approval,
            "show_daily_log_smart_card": self.show_daily_log_smart_card,
            "show_operational_alerts": self.show_operational_alerts,
            "enable_tree_gis_zoning": self.enable_tree_gis_zoning,
            "enable_bulk_cohort_transition": self.enable_bulk_cohort_transition,
            "enable_biocost_depreciation_predictor": self.enable_biocost_depreciation_predictor,
            "default_irrigation_power_source": self.default_irrigation_power_source,
            "offline_cache_retention_days": self.offline_cache_retention_days,
            "synced_draft_retention_days": self.synced_draft_retention_days,
            "dead_letter_retention_days": self.dead_letter_retention_days,
            "enable_offline_media_purge": self.enable_offline_media_purge,
            "enable_offline_conflict_resolution": self.enable_offline_conflict_resolution,
            "enable_predictive_alerts": self.enable_predictive_alerts,
            "enable_local_purge_audit": self.enable_local_purge_audit,
            "enable_pos_barcode": self.enable_pos_barcode,
        }
