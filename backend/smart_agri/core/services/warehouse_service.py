from decimal import Decimal
from django.db import transaction
from smart_agri.core.models.warehouse import BinLocation, InventoryStock
from smart_agri.inventory.models import Item

class WarehouseService:
    def __init__(self, farm):
        self.farm = farm
    
    @transaction.atomic
    def putaway(self, item: Item, bin_code: str, quantity: Decimal, lot_number: str = ''):
        """تخزين صنف في موقع محدد (Bin)"""
        bin_loc = BinLocation.objects.get(
            zone__warehouse__farm=self.farm,
            code=bin_code,
            is_active=True
        )
        stock, created = InventoryStock.objects.get_or_create(
            item=item,
            bin_location=bin_loc,
            lot_number=lot_number,
            defaults={'quantity': quantity}
        )
        if not created:
            stock.quantity += quantity
            stock.save()
            
        # تحديث حجم الموقع (اختياري للرقابة)
        bin_loc.current_volume += quantity
        bin_loc.save()
        return stock
    
    @transaction.atomic
    def pick(self, item: Item, bin_code: str, quantity: Decimal, lot_number: str = ''):
        """صرف صنف من موقع محدد (Pick from Bin)"""
        bin_loc = BinLocation.objects.get(
            zone__warehouse__farm=self.farm,
            code=bin_code,
            is_active=True
        )
        stock = InventoryStock.objects.get(
            item=item,
            bin_location=bin_loc,
            lot_number=lot_number
        )
        if stock.quantity < quantity:
            from django.core.exceptions import ValidationError
            raise ValidationError(f"الكمية غير كافية في الموقع {bin_code}. المتوفر: {stock.quantity}")
            
        stock.quantity -= quantity
        stock.save()
        
        bin_loc.current_volume -= quantity
        bin_loc.save()
        return stock
