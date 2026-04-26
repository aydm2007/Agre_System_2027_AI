"""
Partnership Models — Sharecropping (الشراكة) and Touring (الطواف).

These models implement the YECO agricultural partnership cycle:
1. SharecroppingContract: defines the agreement between institution and farmer.
2. TouringAssessment: pre-harvest committee evaluation (لجنة الطواف).

Key compliance rules enforced here:
- Committee must have ≥3 members (AGENTS.md § Committees Rule)
- Zakat rate is derived from IrrigationType (AGENTS.md § Sovereign Liabilities)
- All financial fields use Decimal(19,4) (AGENTS.md § Data Types)
- farm_id tenant isolation is mandatory (AGENTS.md § Farm Independence)
"""

from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from .base import SoftDeleteModel


class IrrigationType(models.TextChoices):
    """Determines zakat rate per Islamic jurisprudence (فقه الزكاة الزراعية)."""
    RAIN = 'RAIN', 'أمطار / غيول (زكاة 10%)'
    WELL_PUMP = 'WELL_PUMP', 'آبار / طاقة شمسية / ديزل (زكاة 5%)'


class SharecroppingContract(SoftDeleteModel):
    """
    عقد الشراك أو الإيجار مع المزارعين.

    يحدد نسبة المؤسسة من المحصول، ونوع الري (الذي يحدد نسبة الزكاة تلقائياً).
    """
    CONTRACT_TYPE_SHARECROPPING = 'SHARECROPPING'
    CONTRACT_TYPE_RENTAL = 'RENTAL'
    CONTRACT_TYPE_CHOICES = [
        (CONTRACT_TYPE_SHARECROPPING, 'شراكة (مناصبة)'),
        (CONTRACT_TYPE_RENTAL, 'إيجار'),
    ]

    farm = models.ForeignKey(
        'core.Farm', on_delete=models.PROTECT,
        related_name='sharecropping_contracts',
    )
    farmer_name = models.CharField(max_length=255, help_text="اسم المزارع الشريك")
    farmer_id_number = models.CharField(
        max_length=30, blank=True, default="",
        help_text="رقم هوية المزارع (اختياري)",
    )
    crop = models.ForeignKey(
        'core.Crop', on_delete=models.PROTECT,
        related_name='sharecropping_contracts',
    )
    season = models.ForeignKey(
        'core.Season', on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='sharecropping_contracts',
    )

    contract_type = models.CharField(
        max_length=20,
        choices=CONTRACT_TYPE_CHOICES,
        default=CONTRACT_TYPE_SHARECROPPING,
    )
    irrigation_type = models.CharField(
        max_length=20,
        choices=IrrigationType.choices,
        help_text="نوع الري — يحدد نسبة الزكاة تلقائياً",
    )

    # Institution's share (financial or physical based on FarmSettings.sharecropping_mode)
    institution_percentage = models.DecimalField(
        max_digits=5, decimal_places=4,
        help_text="نسبة المؤسسة (مثال: 0.3000 لـ 30%). تمثل نسبة مالية من الإيراد أو عينية من المحصول حسب إعدادات المزرعة.",
    )

    # Optional rent amount for RENTAL contracts
    annual_rent_amount = models.DecimalField(
        max_digits=19, decimal_places=4,
        null=True, blank=True, default=None,
        help_text="مبلغ الإيجار السنوي (لعقود الإيجار فقط)",
    )

    is_active = models.BooleanField(default=True, db_index=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        managed = True
        db_table = 'core_sharecropping_contract'
        verbose_name = "عقد شراكة / إيجار"
        verbose_name_plural = "عقود الشراكة والإيجارات"
        indexes = [
            models.Index(fields=['farm', 'is_active']),
            models.Index(fields=['farmer_name']),
        ]

    def clean(self):
        super().clean()
        if self.institution_percentage is not None:
            if not (Decimal('0.0000') < self.institution_percentage <= Decimal('1.0000')):
                raise ValidationError(
                    "نسبة المؤسسة يجب أن تكون بين 0 و 1 (مثال: 0.3000 لـ 30%)."
                )
        
        # --- Governance & Integrity: Sharecropping Isolation --- #
        # A SharecroppingContract CANNOT be created if there is an active CropPlan (Technical Operations)
        # for the same crop and season.
        if getattr(self, "farm_id", None) and getattr(self, "season_id", None) and getattr(self, "crop_id", None):
            from smart_agri.core.models.planning import CropPlan
            has_plan = CropPlan.objects.filter(
                farm_id=self.farm_id,
                season_id=self.season_id,
                crop_id=self.crop_id,
                deleted_at__isnull=True
            ).exists()
            if has_plan:
                raise ValidationError(
                    "🔴 [FORENSIC BLOCK] لا يمكن إنشاء عقد شراكة/طواف لمحصول يمتلك خطة عمل فنية (إدارة مباشرة) في نفس الموسم."
                )

    def get_zakat_rate(self) -> Decimal:
        """Returns the zakat rate based on irrigation type."""
        if self.irrigation_type == IrrigationType.RAIN:
            return Decimal('0.1000')  # 10%
        return Decimal('0.0500')  # 5%

    def __str__(self):
        return f"عقد شراك: {self.farmer_name} — {self.farm.name}"


class TouringAssessment(models.Model):
    """
    محضر الطواف (لجنة تقييم المحصول قبل الحصاد).

    Touring is the pre-harvest field assessment where a committee of at least 3
    people inspects the crop and estimates the yield. This creates a "pending
    entitlement" (استحقاق معلق) for the institution's share.

    Enforces: committee >= 3 members (Hard Block, not Shadow).
    """
    contract = models.ForeignKey(
        SharecroppingContract, on_delete=models.PROTECT,
        related_name='touring_assessments',
    )
    assessment_date = models.DateField(auto_now_add=True)

    # Yield estimate (in KG)
    estimated_total_yield_kg = models.DecimalField(
        max_digits=19, decimal_places=4,
        help_text="التقدير الكلي للمحصول بالكيلوجرام",
    )
    expected_zakat_kg = models.DecimalField(
        max_digits=19, decimal_places=4,
        help_text="مقدار الزكاة المتوقعة بالكيلوجرام",
    )
    expected_institution_share_kg = models.DecimalField(
        max_digits=19, decimal_places=4,
        help_text="حصة المؤسسة المتوقعة في حال كانت الشراكة عينية (تترك 0 إذا كانت مالية)",
    )

    # Committee documentation (Hard Block: must be >= 3)
    committee_members = models.JSONField(
        help_text="أسماء وتوقيعات أعضاء لجنة الطواف (مصفوفة). يجب 3 على الأقل.",
    )

    is_harvested = models.BooleanField(
        default=False,
        help_text="هل تم الحصاد الفعلي وإقفال محضر الطواف؟",
    )

    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'core_touring_assessment'
        ordering = ['-assessment_date']
        verbose_name = "محضر طواف (تقييم مسبق)"
        verbose_name_plural = "محاضر الطواف"
        indexes = [
            models.Index(fields=['contract', 'is_harvested']),
        ]

    def clean(self):
        super().clean()
        if not isinstance(self.committee_members, list) or len(self.committee_members) < 3:
            raise ValidationError(
                "🔴 [FORENSIC BLOCK] محضر الطواف باطل. "
                "يجب تشكيل لجنة من 3 أشخاص على الأقل."
            )

    def __str__(self):
        return (
            f"طواف: {self.contract.farmer_name} — "
            f"تقدير: {self.estimated_total_yield_kg} كجم"
        )


class SharecroppingReceipt(SoftDeleteModel):
    """
    سند استلام شراكة (مالي أو عيني).
    يتم إنشاؤه بناءً على محضر طواف، ويمثل الاستلام النهائي لحصة المؤسسة.
    """
    RECEIPT_TYPE_FINANCIAL = 'FINANCIAL'
    RECEIPT_TYPE_PHYSICAL = 'PHYSICAL'
    RECEIPT_TYPE_CHOICES = [
        (RECEIPT_TYPE_FINANCIAL, 'استلام مالي (من الأرباح/الإيرادات)'),
        (RECEIPT_TYPE_PHYSICAL, 'استلام عيني (محصول)'),
    ]

    farm = models.ForeignKey(
        'core.Farm', on_delete=models.PROTECT,
        related_name='sharecropping_receipts',
    )
    assessment = models.ForeignKey(
        TouringAssessment, on_delete=models.PROTECT,
        related_name='receipts',
    )
    receipt_date = models.DateField(default=timezone.now)
    receipt_type = models.CharField(
        max_length=20,
        choices=RECEIPT_TYPE_CHOICES,
    )

    # For FINANCIAL receipt
    amount_received = models.DecimalField(
        max_digits=19, decimal_places=4,
        null=True, blank=True,
        help_text="المبلغ المالي المستلم (لحالات الاستلام المالي)",
    )

    # For PHYSICAL receipt
    quantity_received_kg = models.DecimalField(
        max_digits=19, decimal_places=4,
        null=True, blank=True,
        help_text="الكمية العينية المستلمة بالكيلوجرام",
    )
    destination_inventory = models.ForeignKey(
        'inventory.ItemInventory', on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='sharecropping_receipts',
        help_text="المخزن أو الصومعة المستقبلة للمحصول العيني",
    )

    # General
    received_by = models.ForeignKey(
        'auth.User', on_delete=models.PROTECT,
        related_name='received_sharecropping',
    )
    is_posted = models.BooleanField(
        default=False,
        help_text="هل تم الترحيل لدفتر الأستاذ المالي/المخزني؟",
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'core_sharecropping_receipt'
        ordering = ['-receipt_date']
        verbose_name = "سند استلام شراكة"
        verbose_name_plural = "سندات استلام الشراكة"
        indexes = [
            models.Index(fields=['farm', 'receipt_date']),
            models.Index(fields=['is_posted']),
        ]

    def clean(self):
        super().clean()
        if self.receipt_type == self.RECEIPT_TYPE_FINANCIAL:
            if not self.amount_received or self.amount_received <= 0:
                raise ValidationError("يجب إدخال مبلغ استلام صحيح في السند المالي.")
        elif self.receipt_type == self.RECEIPT_TYPE_PHYSICAL:
            if not self.quantity_received_kg or self.quantity_received_kg <= 0:
                raise ValidationError("يجب إدخال كمية صحيحة في السند العيني.")
            if not self.destination_inventory:
                raise ValidationError("يجب تحديد مستودع وجهة للمحصول العيني.")

    def __str__(self):
        if self.receipt_type == self.RECEIPT_TYPE_FINANCIAL:
            return f"سند شراكة (مالي) #{self.id} — {self.amount_received}"
        return f"سند شراكة (عيني) #{self.id} — {self.quantity_received_kg} كجم"
