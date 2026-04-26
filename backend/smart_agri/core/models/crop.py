from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError
from .base import SoftDeleteModel
from .farm import Farm
# from .inventory import Item, Unit
from smart_agri.inventory.models import Item, Unit

class Crop(SoftDeleteModel):
    MODE_CHOICES = [("Open", "Open"), ("Protected", "Protected")]
    name = models.CharField(max_length=100)
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default="Open")
    is_perennial = models.BooleanField(default=False)
    
    # [NEW] مصفوفة المهام: ما هي المهام المسموحة لهذا المحصول؟
    supported_tasks = models.ManyToManyField(
        'core.Task',
        blank=True,
        related_name='supported_crops',
        verbose_name="العمليات الزراعية المدعومة"
    )

    # [Protocol XVIII] Bio-Constraints Enforcement
    # Biological Limits (The Laws of Nature)
    max_yield_per_ha = models.DecimalField(
        max_digits=12, decimal_places=3, default=0, help_text="Maximum biological yield per Hectare (Tonnes)"
    )
    max_yield_per_tree = models.DecimalField(
        max_digits=10, decimal_places=3, default=0, help_text="Maximum biological yield per Tree (Kg)"
    )
    
    # Phenological Lock (Cycle Validation)
    # Json Schema: { "stages": ["Vegetative", "Flowering", "Fruiting"], "allowed_actions": { "Harvest": ["Fruiting"] } }
    phenological_stages = models.JSONField(
        default=dict, blank=True, help_text="Defines growth stages and disallowed actions per stage."
    )

    class Meta:
        unique_together = ("name", "mode")
        verbose_name = "محصول محوري"
        verbose_name_plural = "المحاصيل المحورية"
        indexes = [models.Index(fields=["name", "mode"])]

    def __str__(self):
        return f"{self.name} ({self.mode})"

class FarmCrop(SoftDeleteModel):
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="farm_crops")
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name="farm_links")

    class Meta:
        unique_together = ("farm", "crop")
        verbose_name = "محصول المزرعة"
        verbose_name_plural = "محاصيل المزارع"
        indexes = [models.Index(fields=["farm", "crop"])]

    def __str__(self):
        return f"{self.farm} -> {self.crop}"

class CropVariety(SoftDeleteModel):
    """
    أصناف المحصول (مثلاً: مانجو -> تيمور، عويس، قلب الثور)
    """
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name="varieties_list", null=True, blank=True)
    name = models.CharField(max_length=100, verbose_name="اسم الصنف")
    code = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField(blank=True, default="")
    
    # خصائص الصنف
    est_days_to_harvest = models.IntegerField(default=90, verbose_name="دورة النمو (يوم)")
    expected_yield_per_ha = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="الإنتاجية المتوقعة/هكتار")

    class Meta:
        db_table = 'core_crop_variety'
        unique_together = ('crop', 'name')
        verbose_name = "صنف زراعي"

    def __str__(self):
        try:
            crop_name = self.crop.name if self.crop else "Unassigned"
        except (AttributeError, ValueError, TypeError):
            crop_name = "None"
        return f"{crop_name} - {self.name}"

class CropProduct(SoftDeleteModel):
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=150)
    is_primary = models.BooleanField(default=False)
    pack_size = models.DecimalField(max_digits=10, decimal_places=2, default=1.0, null=True, blank=True)
    pack_uom = models.CharField(max_length=40, default="kg")
    item = models.ForeignKey(
        "inventory.Item",
        on_delete=models.CASCADE,
        related_name="crop_products",
    )
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, null=True, blank=True)
    packing_type = models.CharField(max_length=80, blank=True, default="")
    quality_grade = models.CharField(max_length=50, blank=True, default="")
    reference_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    notes = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        managed = True
        db_table = 'core_cropproduct'
        verbose_name = "Crop Product"

    def save(self, *args, **kwargs):
        if not self.item_id:
            fallback_uom = (self.pack_uom or "").strip() or "Unit"
            fallback_item, _ = Item.objects.get_or_create(
                name=self.name,
                group="Produce",
                defaults={"uom": fallback_uom},
            )
            self.item = fallback_item
        result = super().save(*args, **kwargs)
        if self.is_primary:
            CropProduct.objects.filter(
                crop=self.crop,
                deleted_at__isnull=True,
            ).exclude(pk=self.pk).update(is_primary=False)
        return result

class CropProductUnit(SoftDeleteModel):
    product = models.ForeignKey(
        CropProduct,
        on_delete=models.CASCADE,
        related_name="unit_options",
    )
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="crop_product_units")
    uom = models.CharField(max_length=40, blank=True, default="")
    multiplier = models.DecimalField(max_digits=18, decimal_places=8)
    is_default = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "unit"],
                condition=Q(deleted_at__isnull=True),
                name="cropproductunit_product_unit_uc",
            )
        ]
        indexes = [
            models.Index(fields=["product", "unit"]),
            models.Index(fields=["product", "is_default"]),
        ]

    def clean(self):
        super().clean()
        if self.multiplier is None or self.multiplier <= 0:
            raise ValidationError({"multiplier": "Multiplier must be greater than zero."})
        if not self.uom and self.unit_id:
            symbol = getattr(self.unit, "symbol", None) or getattr(self.unit, "code", "")
            self.uom = symbol or ""

    def save(self, *args, **kwargs):
        self.full_clean()
        result = super().save(*args, **kwargs)
        if self.is_default:
            CropProductUnit.objects.filter(
                product=self.product,
                deleted_at__isnull=True,
            ).exclude(pk=self.pk).update(is_default=False)
        return result

class CropMaterial(SoftDeleteModel):
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name="material_links")
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="crop_material_links")
    is_primary = models.BooleanField(default=False)
    recommended_qty = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    recommended_uom = models.CharField(max_length=40, blank=True, default="")
    recommended_unit = models.ForeignKey(
        Unit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recommended_materials",
    )
    notes = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        unique_together = ("crop", "item")
        indexes = [
            models.Index(fields=["crop", "item"]),
            models.Index(fields=["crop", "is_primary"]),
        ]

    def clean(self):
        super().clean()
        if self.recommended_qty is not None and self.recommended_qty < 0:
            raise ValidationError({"recommended_qty": "القيمة يجب أن تكون موجبة."})
        if self.is_primary:
            existing = CropMaterial.objects.filter(
                crop=self.crop,
                is_primary=True,
                deleted_at__isnull=True,
            )
            if self.pk:
                existing = existing.exclude(pk=self.pk)
            if existing.exists():
                raise ValidationError({
                    "is_primary": "تم تحديد مادة أساسية لهذا المحصول مسبقاً.",
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        result = super().save(*args, **kwargs)
        if self.is_primary:
            CropMaterial.objects.filter(
                crop=self.crop,
                deleted_at__isnull=True,
            ).exclude(pk=self.pk).update(is_primary=False)
        return result

class CropRecipe(SoftDeleteModel):
    """
    الوصفة الزراعية المعيارية (Agronomic BOM)
    تستخدم لتحديد التكاليف المعيارية وتوقع كميات ونوعيات المواد (أسمدة، مبيدات، عمالة) 
    في كل مرحلة نمو للمحصول قبل التنفيذ لتمكين مقارنة الانحراف.
    """
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name="recipes")
    name = models.CharField(max_length=150, help_text="اسم الوصفة (مثال: تسميد عنب أسبوع 1)")
    phenological_stage = models.CharField(max_length=50, blank=True, null=True, help_text="مرحلة النمو المستهدفة (مثال: تزهير، إثمار)")
    expected_labor_hours_per_ha = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'core_croprecipe'
        verbose_name = "مواصفة زراعية قياسية"
        ordering = ['crop', 'name']

    def __str__(self):
        return f"[{self.crop.name}] {self.name}"

class CropRecipeMaterial(SoftDeleteModel):
    """
    عناصر الوصفة (Standard Materials)
    ما هي المواد المستهلكة المتوقعة لكل هكتار ضمن هذه الوصفة.
    """
    recipe = models.ForeignKey(CropRecipe, on_delete=models.CASCADE, related_name="materials")
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="recipe_usages")
    standard_qty_per_ha = models.DecimalField(max_digits=12, decimal_places=3, help_text="الكمية المعيارية لكل هكتار")
    
    class Meta:
        db_table = 'core_croprecipe_material'
        verbose_name = "مادة قياسية"
        unique_together = ('recipe', 'item')

    def __str__(self):
        return f"{self.item.name}: {self.standard_qty_per_ha}/ha"

class CropRecipeTask(SoftDeleteModel):
    """
    المهام القياسية للوصفة (Standard Activities)
    تحديد المهام المتوقعة، توقيتها النسبي، والجهد العمالي المتوقع.
    """
    recipe = models.ForeignKey(CropRecipe, on_delete=models.CASCADE, related_name="tasks")
    task = models.ForeignKey('core.Task', on_delete=models.SET_NULL, null=True, blank=True, related_name="recipe_links")
    stage = models.CharField(max_length=50, blank=True, default="", help_text="المرحلة المستهدفة")
    name = models.CharField(max_length=200, help_text="اسم المهمة التفصيلي")
    days_offset = models.PositiveIntegerField(
        default=0, 
        help_text="اليوم الذي تبدأ فيه المهمة نسبة لبداية تفعيل الوصفة"
    )
    estimated_hours = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = 'core_croprecipe_task'
        verbose_name = "مهمة قياسية"
        ordering = ['days_offset', 'id']

    def __str__(self):
        return f"{self.name} (T+{self.days_offset})"
