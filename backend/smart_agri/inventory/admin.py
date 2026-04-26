from django.contrib import admin
from smart_agri.inventory.models import (
    Unit,
    UnitConversion,
    ItemInventory,
    ItemInventoryBatch,
    TankCalibration,
    FuelLog,
    StockMovement,
)


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'symbol', 'category', 'precision')
    list_filter = ('category',)
    search_fields = ('code', 'name')


@admin.register(UnitConversion)
class UnitConversionAdmin(admin.ModelAdmin):
    list_display = ('from_unit', 'to_unit', 'multiplier')
    raw_id_fields = ('from_unit', 'to_unit')





@admin.register(ItemInventory)
class ItemInventoryAdmin(admin.ModelAdmin):
    list_display = ('farm', 'item', 'location', 'qty', 'uom')
    list_filter = ('farm',)
    raw_id_fields = ('farm', 'location', 'item')


@admin.register(ItemInventoryBatch)
class ItemInventoryBatchAdmin(admin.ModelAdmin):
    list_display = ('inventory', 'batch_number', 'qty', 'expiry_date')
    raw_id_fields = ('inventory',)


@admin.register(TankCalibration)
class TankCalibrationAdmin(admin.ModelAdmin):
    list_display = ('asset', 'cm_reading', 'liters_volume')
    raw_id_fields = ('asset',)


@admin.register(FuelLog)
class FuelLogAdmin(admin.ModelAdmin):
    list_display = ('farm', 'asset_tank', 'supervisor', 'reading_date', 'liters_consumed')
    list_filter = ('farm', 'measurement_method')
    raw_id_fields = ('farm', 'asset_tank', 'supervisor')


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('farm', 'item', 'location', 'qty_delta', 'ref_type', 'ref_id')
    list_filter = ('farm', 'ref_type')
    raw_id_fields = ('farm', 'item', 'location')
