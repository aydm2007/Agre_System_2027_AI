
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, F
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from django.conf import settings

# Base Model Import (Assuming shared Base)
# We might need to duplicate SoftDeleteModel or import it if it's generic.
# For now, let's assume we import it from core to avoid redefining logic, 
from smart_agri.core.models.base import SoftDeleteModel
from smart_agri.core.constants import StandardUOM

class MaterialType(models.TextChoices):
    FERTILIZER = "FERTILIZER", "أسمدة"
    PESTICIDE = "PESTICIDE", "مبيدات"
    SEED = "SEED", "بذور"
    FUEL = "FUEL", "وقود"
    FEED = "FEED", "أعلاف"
    PACKAGING = "PACKAGING", "تعبئة وتغليف"
    SPARE_PARTS = "SPARE_PARTS", "قطع غيار"
    TOOLS = "TOOLS", "أدوات"
    ORGANIC = "ORGANIC", "أسمدة عضوية"
    CHEMICAL = "CHEMICAL", "كيماويات"
    OTHER = "OTHER", "أخرى"

class Unit(SoftDeleteModel):
    CATEGORY_MASS = "mass"
    CATEGORY_VOLUME = "volume"
    CATEGORY_COUNT = "count"
    CATEGORY_AREA = "area"
    CATEGORY_LENGTH = "length"
    CATEGORY_TIME = "time"
    CATEGORY_OTHER = "other"
    CATEGORY_CHOICES = [
        (CATEGORY_MASS, "Mass"),
        (CATEGORY_VOLUME, "Volume"),
        (CATEGORY_COUNT, "Count"),
        (CATEGORY_AREA, "Area"),
        (CATEGORY_LENGTH, "Length"),
        (CATEGORY_TIME, "Time"),
        (CATEGORY_OTHER, "Other"),
    ]

    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=120)
    symbol = models.CharField(max_length=20, blank=True, default="")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default=CATEGORY_OTHER)
    precision = models.PositiveSmallIntegerField(default=3)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'core_unit' # Safe-Move: Keep old table
        verbose_name = "وحدة قياس"
        verbose_name_plural = "وحدات القياس"
        ordering = ["category", "name", "code"]
    
    def clean(self):
        super().clean()
        if not self.code:
             raise ValidationError({"code": "رمز الوحدة لا يمكن أن يكون فارغاً."})

class UnitConversion(SoftDeleteModel):
    from_unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="conversions_from")
    to_unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="conversions_to")
    multiplier = models.DecimalField(max_digits=18, decimal_places=8)

    class Meta:
        db_table = 'core_unitconversion' # Safe-Move
        verbose_name = "تحويل الوحدة"
        verbose_name_plural = "تحويلات الوحدات"
        unique_together = ("from_unit", "to_unit")
        indexes = [models.Index(fields=["from_unit", "to_unit"])]

class Item(SoftDeleteModel):
    def __init__(self, *args, **kwargs):
        legacy_type = kwargs.pop("type", None)
        if legacy_type and "group" not in kwargs:
            kwargs["group"] = str(legacy_type).title()
        super().__init__(*args, **kwargs)

    name = models.CharField(max_length=150)
    group = models.CharField(max_length=60, default="General")
    material_type = models.CharField(
        max_length=20,
        choices=MaterialType.choices,
        default=MaterialType.OTHER,
        verbose_name="نوع المادة",
        help_text="تصنيف المادة: أسمدة، مبيدات، بذور، وقود، إلخ",
        db_index=True,
    )
    uom = models.CharField(max_length=40, choices=StandardUOM.choices, default=StandardUOM.UNIT)
    unit = models.ForeignKey(
        Unit, 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True, 
        related_name="items",
        verbose_name="وحدة القياس المعتمدة",
        help_text="FK لوحدة القياس الهيكلية (لتر، كجم، إلخ). uom يبقى للتوافقية فقط.",
    )
    unit_price = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    currency = models.CharField(max_length=8, default="YER")
    reorder_level = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    
    # [Agri-Guardian] Chemical Safety
    phi_days = models.PositiveIntegerField(default=0, help_text="Pre-Harvest Interval in days. (فترة التحريم)")
    
    # [Agri-Guardian] GlobalGAP Compliance
    requires_batch_tracking = models.BooleanField(
        default=False, 
        help_text="تتبع صارم للتشغيلة وتاريخ الانتهاء (GlobalGAP)"
    )
    
    is_saleable = models.BooleanField(
        default=False,
        help_text="يمكن بيع الصنف عبر نقاط البيع (POS)"
    )

    class Meta:
        db_table = 'core_item' # Safe-Move
        verbose_name = "مادة/صنف"
        verbose_name_plural = "المواد والأصناف"
        unique_together = ("name", "group")

class ItemInventory(SoftDeleteModel):
    # String References to Core Models
    farm = models.ForeignKey('core.Farm', on_delete=models.CASCADE, related_name="item_inventories_new")
    location = models.ForeignKey('core.Location', null=True, blank=True, on_delete=models.SET_NULL, related_name="item_inventories_new")
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="inventories")
    crop_plan = models.ForeignKey(
        'core.CropPlan',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="allocated_inventory",
        verbose_name="خطة المحصول",
        help_text="تخصيص اختياري لرصيد المخزون لصالح خطة محصول معينة",
    )
    qty = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    uom = models.CharField(max_length=40, choices=StandardUOM.choices, blank=True, default="")
    # updated_at provided by SoftDeleteModel

    # [AGRI-GUARDIAN] Offline Conflict Resolution Columns (SQL Patch Sync)
    device_last_modified_at = models.DateTimeField(null=True, blank=True, help_text="Last modification time on client device")
    sync_version = models.BigIntegerField(default=1, help_text="Lamport Clock / Version Vector")

    class Meta:
        db_table = 'core_item_inventory'
        verbose_name = "مخزون المادة"
        verbose_name_plural = "مخزون المواد"
        unique_together = ("farm", "location", "item", "crop_plan")
        indexes = [models.Index(fields=["farm", "item"]), models.Index(fields=["location"])]
        constraints = [
            models.UniqueConstraint(
                fields=("farm", "item"),
                condition=Q(location__isnull=True),
                name="iteminventory_farm_item_null_location_uc_v2", # Renamed to avoid collision if run concurrently, though db_table is same
            ),
            # Hard Quality Gate: DB Constraint
            models.CheckConstraint(check=Q(qty__gte=0), name="iteminventory_qty_non_negative_v2"),
        ]

class ItemInventoryBatch(models.Model):
    inventory = models.ForeignKey(ItemInventory, on_delete=models.CASCADE, related_name="batches")
    batch_number = models.CharField(max_length=100)
    expiry_date = models.DateField(null=True, blank=True)
    qty = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_item_inventory_batch'
        verbose_name = "دفعة مخزون المادة"
        verbose_name_plural = "دفعات مخزون المواد"
        unique_together = ("inventory", "batch_number")
        indexes = [models.Index(fields=["inventory", "batch_number"])]
        constraints = [
            models.CheckConstraint(check=Q(qty__gte=0), name="iteminventorybatch_qty_non_negative_v2")
        ]

class TankCalibration(models.Model):
    """
    Table to convert Dipstick (cm) readings to Liters for Diesel Tanks.
    """
    asset = models.ForeignKey(
        'core.Asset',
        on_delete=models.CASCADE,
        related_name='calibrations',
        limit_choices_to={'asset_type': 'tank'},
    )
    cm_reading = models.DecimalField(max_digits=6, decimal_places=2, help_text="Reading in CM")
    liters_volume = models.DecimalField(max_digits=19, decimal_places=4, help_text="Equivalent Liters")

    class Meta:
        verbose_name = "معايرة الخزان"
        verbose_name_plural = "معايرات الخزانات"
        db_table = 'inventory_tankcalibration'
        unique_together = ('asset', 'cm_reading')
        ordering = ['asset', 'cm_reading']

    def clean(self):
        super().clean()
        if self.cm_reading is None or self.cm_reading < 0:
            raise ValidationError({"cm_reading": "Dipstick reading cannot be negative."})
        if self.liters_volume is None or self.liters_volume < 0:
            raise ValidationError({"liters_volume": "Liters value cannot be negative."})


class FuelLog(models.Model):
    """
    Specialized log for Diesel consumption using Dipstick readings.
    """
    MEASUREMENT_METHOD_DIPSTICK = "DIPSTICK"
    MEASUREMENT_METHOD_COUNTER = "COUNTER"
    MEASUREMENT_METHODS = [
        (MEASUREMENT_METHOD_DIPSTICK, "Manual Dipstick (Sikh)"),
        (MEASUREMENT_METHOD_COUNTER, "Mechanical Counter"),
    ]

    farm = models.ForeignKey('core.Farm', on_delete=models.CASCADE)
    asset_tank = models.ForeignKey('core.Asset', on_delete=models.PROTECT)
    supervisor = models.ForeignKey('core.Supervisor', on_delete=models.PROTECT, related_name='fuel_logs')
    reading_date = models.DateTimeField(default=timezone.now)
    measurement_method = models.CharField(
        max_length=20,
        choices=MEASUREMENT_METHODS,
        default=MEASUREMENT_METHOD_DIPSTICK,
    )
    reading_start_cm = models.DecimalField(max_digits=6, decimal_places=2)
    reading_end_cm = models.DecimalField(max_digits=6, decimal_places=2)
    liters_consumed = models.DecimalField(max_digits=19, decimal_places=4, editable=False)

    class Meta:
        db_table = 'inventory_fuellog'
        verbose_name = "يومية وقود"
        verbose_name_plural = "يوميات الوقود"
        indexes = [models.Index(fields=['farm', 'asset_tank'])]

    def clean(self):
        super().clean()
        if self.measurement_method not in {
            self.MEASUREMENT_METHOD_DIPSTICK,
            self.MEASUREMENT_METHOD_COUNTER,
        }:
            raise ValidationError("IoT/Sensor readings are strictly prohibited. Use Manual Dipstick.")
        if self.reading_start_cm is None or self.reading_end_cm is None:
            raise ValidationError("Dipstick readings are required.")
        if self.reading_start_cm < 0 or self.reading_end_cm < 0:
            raise ValidationError("Dipstick readings cannot be negative.")
        if self.reading_start_cm < self.reading_end_cm:
            raise ValidationError("Start reading must be greater than or equal to end reading.")

    def save(self, *args, **kwargs):
        self.full_clean()
        with transaction.atomic():
            start_vol = self.get_liters(self.asset_tank, self.reading_start_cm)
            end_vol = self.get_liters(self.asset_tank, self.reading_end_cm)
            self.liters_consumed = (start_vol - end_vol).quantize(Decimal("0.0001"))
            super().save(*args, **kwargs)

    @staticmethod
    def get_liters(asset, cm):
        lower = (
            TankCalibration.objects.select_for_update()
            .filter(asset=asset, cm_reading__lte=cm)
            .order_by('-cm_reading')
            .first()
        )
        if not lower:
            raise ValidationError("No calibration entry found for the provided dipstick reading.")

        upper = (
            TankCalibration.objects.select_for_update()
            .filter(asset=asset, cm_reading__gte=cm)
            .order_by('cm_reading')
            .first()
        )

        if not upper or lower.cm_reading == upper.cm_reading:
            return lower.liters_volume

        cm_delta = Decimal(upper.cm_reading) - Decimal(lower.cm_reading)
        if cm_delta == Decimal("0"):
            return lower.liters_volume

        # [AGRI-GUARDIAN] Strict Context Division avoids loose float inferences
        from decimal import getcontext
        ratio = getcontext().divide(Decimal(cm) - Decimal(lower.cm_reading), Decimal(str(cm_delta))).quantize(Decimal("0.00000001"))
        liters = Decimal(lower.liters_volume) + (
            ratio * (Decimal(upper.liters_volume) - Decimal(lower.liters_volume))
        )
        return liters.quantize(Decimal("0.0001"))

class StockMovement(SoftDeleteModel):
    farm = models.ForeignKey('core.Farm', on_delete=models.CASCADE, related_name="stock_movements_new")
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="movements")
    location = models.ForeignKey('core.Location', on_delete=models.SET_NULL, null=True, blank=True, related_name="stock_movements_new")
    qty_delta = models.DecimalField(max_digits=12, decimal_places=3)
    ref_type = models.CharField(max_length=50, blank=True, default="")
    ref_id = models.CharField(max_length=50, blank=True, default="")
    note = models.CharField(max_length=250, blank=True, default="")
    batch_number = models.CharField(max_length=100, null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    unit_cost = models.DecimalField(max_digits=19, decimal_places=4, null=True, blank=True)

    class Meta:
        db_table = 'core_stockmovement'
        verbose_name = "حركة مخزون"
        verbose_name_plural = "حركات المخزون"
        constraints = [
            models.CheckConstraint(check=~Q(qty_delta=0), name="stockmovement_delta_not_zero_v2")
        ]
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['ref_id']),
            models.Index(fields=['farm', 'item']),
        ]


def _legacy_apply_stockmovement_delta(*, farm_id, item_id, location_id, qty_delta, batch_number=None):
    qty_delta = Decimal(str(qty_delta or 0))
    inventory, _ = ItemInventory.objects.get_or_create(
        farm_id=farm_id,
        item_id=item_id,
        location_id=location_id,
        defaults={"qty": Decimal("0"), "uom": ""},
    )
    new_qty = (inventory.qty or Decimal("0")) + qty_delta
    if new_qty < 0:
        new_qty = Decimal("0")
    inventory.qty = new_qty
    if not inventory.uom:
        inventory.uom = getattr(inventory.item, "uom", "") or ""
    inventory.save(update_fields=["qty", "uom", "updated_at"])

    bn = str(batch_number).strip() if batch_number else "AUTO"
    batch, _ = ItemInventoryBatch.objects.get_or_create(
        inventory=inventory,
        batch_number=bn,
        defaults={"qty": Decimal("0")},
    )
    batch_qty = (batch.qty or Decimal("0")) + qty_delta
    if batch_qty < 0:
        batch_qty = Decimal("0")
    batch.qty = batch_qty
    batch.save(update_fields=["qty", "updated_at"])

def _apply_wac_if_inward(instance):
    if instance.qty_delta > 0 and instance.unit_cost is not None:
        item = instance.item
        from django.db.models import Sum
        current_qty = item.inventories.aggregate(total=Sum('qty'))['total'] or Decimal('0')
        previous_qty = current_qty - instance.qty_delta
        if previous_qty < Decimal('0'):
            previous_qty = Decimal('0')
            
        current_wac = item.unit_price or Decimal('0')
        new_total_value = (previous_qty * current_wac) + (instance.qty_delta * instance.unit_cost)
        new_total_qty = previous_qty + instance.qty_delta
        
        if new_total_qty > 0:
            new_wac = (new_total_value / new_total_qty).quantize(Decimal('0.001'))  # agri-guardian: decimal-safe
            item.unit_price = new_wac
            item.save(update_fields=['unit_price'])

@receiver(pre_save, sender=StockMovement)
def _legacy_stockmovement_capture_previous(sender, instance, **kwargs):
    if not instance.pk:
        instance._legacy_previous = None
        return
    try:
        prev = sender.objects.get(pk=instance.pk)
        instance._legacy_previous = prev
    except sender.DoesNotExist:
        instance._legacy_previous = None


@receiver(post_save, sender=StockMovement)
def _legacy_stockmovement_apply(sender, instance, created, **kwargs):
    if getattr(sender, "_skip_legacy_sync", False):
        return
    if instance.ref_type in {"activity", "harvest_activity"}:
        return
    if created:
        _legacy_apply_stockmovement_delta(
            farm_id=instance.farm_id,
            item_id=instance.item_id,
            location_id=instance.location_id,
            qty_delta=instance.qty_delta,
            batch_number=instance.batch_number,
        )
        _apply_wac_if_inward(instance)
        return

    prev = getattr(instance, "_legacy_previous", None)
    if prev is None:
        _legacy_apply_stockmovement_delta(
            farm_id=instance.farm_id,
            item_id=instance.item_id,
            location_id=instance.location_id,
            qty_delta=instance.qty_delta,
            batch_number=instance.batch_number,
        )
        return

    if prev.deleted_at is None and instance.deleted_at is not None:
        _legacy_apply_stockmovement_delta(
            farm_id=prev.farm_id,
            item_id=prev.item_id,
            location_id=prev.location_id,
            qty_delta=-(prev.qty_delta),
            batch_number=prev.batch_number,
        )
        return

    _legacy_apply_stockmovement_delta(
        farm_id=prev.farm_id,
        item_id=prev.item_id,
        location_id=prev.location_id,
        qty_delta=-(prev.qty_delta),
        batch_number=prev.batch_number,
    )
    _legacy_apply_stockmovement_delta(
        farm_id=instance.farm_id,
        item_id=instance.item_id,
        location_id=instance.location_id,
        qty_delta=instance.qty_delta,
        batch_number=instance.batch_number,
    )


@receiver(post_delete, sender=StockMovement)
def _legacy_stockmovement_reverse(sender, instance, **kwargs):
    if getattr(sender, "_skip_legacy_sync", False):
        return
    if instance.ref_type in {"activity", "harvest_activity"}:
        return
    _legacy_apply_stockmovement_delta(
        farm_id=instance.farm_id,
        item_id=instance.item_id,
        location_id=instance.location_id,
        qty_delta=-(instance.qty_delta),
        batch_number=instance.batch_number,
    )

class PurchaseOrder(SoftDeleteModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "مسودة"
        PENDING_TECHNICAL = "PENDING_TECHNICAL", "قيد المراجعة الفنية"
        PENDING_FINANCIAL = "PENDING_FINANCIAL", "قيد المراجعة المالية"
        PENDING_DIRECTOR = "PENDING_DIRECTOR", "قيد اعتماد المدير"
        APPROVED = "APPROVED", "معتمد"
        REJECTED = "REJECTED", "مرفوض"
        RECEIVED = "RECEIVED", "مستلم"
        CANCELED = "CANCELED", "ملغي"

    farm = models.ForeignKey('core.Farm', on_delete=models.CASCADE, related_name="purchase_orders", verbose_name="المزرعة")
    vendor_name = models.CharField(max_length=200, verbose_name="اسم المورد", help_text="اسم المورد")
    order_date = models.DateField(default=timezone.now, verbose_name="تاريخ الطلب")
    expected_delivery_date = models.DateField(null=True, blank=True, verbose_name="تاريخ التوصيل المتوقع")
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.DRAFT, verbose_name="حالة الطلب")
    total_amount = models.DecimalField(max_digits=19, decimal_places=4, default=0, verbose_name="الإجمالي")
    currency = models.CharField(max_length=10, default="YER", verbose_name="العملة")
    
    # Signatures
    technical_signature = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="po_tech_signed", verbose_name="توقيع الفني")
    financial_signature = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="po_fin_signed", verbose_name="توقيع المالي")
    director_signature = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="po_dir_signed", verbose_name="توقيع المدير")

    rejection_reason = models.TextField(blank=True, default="", verbose_name="سبب الرفض")
    notes = models.TextField(blank=True, default="", verbose_name="ملاحظات")

    class Meta:
        db_table = 'inventory_purchaseorder'
        verbose_name = "طلب شراء"
        verbose_name_plural = "طلبات الشراء"

    @property
    def is_high_value(self):
        try:
            return self.total_amount >= self.farm.settings.procurement_committee_threshold
        except (AttributeError, ObjectDoesNotExist, TypeError):
            return False

class PurchaseOrderItem(SoftDeleteModel):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="items", verbose_name="طلب الشراء")
    item = models.ForeignKey(Item, on_delete=models.PROTECT, verbose_name="الصنف")
    qty = models.DecimalField(max_digits=12, decimal_places=3, verbose_name="الكمية")
    unit_price = models.DecimalField(max_digits=19, decimal_places=4, verbose_name="سعر الوحدة")
    total_price = models.DecimalField(max_digits=19, decimal_places=4, editable=False, verbose_name="السعر الإجمالي")

    class Meta:
        db_table = 'inventory_purchaseorderitem'
        verbose_name = "بند طلبشراء"
        verbose_name_plural = "بنود طلبات الشراء"

    def save(self, *args, **kwargs):
        self.total_price = self.qty * self.unit_price
        super().save(*args, **kwargs)
        # Update PO total
        total = sum(i.total_price for i in self.purchase_order.items.all() if not i.deleted_at)
        self.purchase_order.total_amount = total
        self.purchase_order.save(update_fields=['total_amount', 'updated_at'])
