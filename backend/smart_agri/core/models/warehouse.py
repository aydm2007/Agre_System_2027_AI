from django.db import models
from smart_agri.core.models.base import SoftDeleteModel
from smart_agri.core.models.farm import Farm
from smart_agri.inventory.models import Item

class Warehouse(SoftDeleteModel):
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="warehouses")
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    location_str = models.CharField(max_length=255, blank=True, verbose_name="الموقع الجغرافي")
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "مستودع"
        verbose_name_plural = "المستودعات"
        unique_together = ['farm', 'code']

class WarehouseZone(SoftDeleteModel):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='zones')
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    zone_type = models.CharField(max_length=20, choices=[
        ('bulk', 'تخزين سائب'),
        ('rack', 'رفوف'),
        ('cold', 'تبريد'),
        ('quarantine', 'حجر صحي')
    ])
    
    class Meta:
        verbose_name = "منطقة تخزين"
        verbose_name_plural = "منطق التخزين"
        unique_together = ['warehouse', 'code']

class BinLocation(SoftDeleteModel):
    zone = models.ForeignKey(WarehouseZone, on_delete=models.CASCADE, related_name='bins')
    code = models.CharField(max_length=30)
    barcode = models.CharField(max_length=100, blank=True)
    capacity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    current_volume = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "موقع دقيق (Bin)"
        verbose_name_plural = "المواقع الدقيقة"
        unique_together = ['zone', 'code']

class InventoryStock(SoftDeleteModel):
    """
    Detailed mapping of item quantities to specific bin locations.
    """
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="bin_stocks")
    bin_location = models.ForeignKey(BinLocation, on_delete=models.CASCADE, related_name="item_stocks")
    quantity = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    lot_number = models.CharField(max_length=50, blank=True)
    
    class Meta:
        verbose_name = "رصيد موقع"
        verbose_name_plural = "أرصدة المواقع"
        unique_together = ['item', 'bin_location', 'lot_number']
