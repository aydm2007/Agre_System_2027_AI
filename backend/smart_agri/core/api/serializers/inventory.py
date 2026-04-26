from rest_framework import serializers
from smart_agri.core.models import (
    Item, ItemInventory, StockMovement, HarvestLot,
    CropProduct, Unit, Crop
)
from .item import ItemSerializer
from .unit import UnitSerializer

class ItemInventorySerializer(serializers.ModelSerializer):
    unit_price = serializers.DecimalField(source='item.unit_price', max_digits=12, decimal_places=3, read_only=True)
    item_name = serializers.CharField(source='item.name', read_only=True)
    low_stock = serializers.SerializerMethodField()

    def get_low_stock(self, obj):
        reorder = getattr(obj.item, "reorder_level", None) or 0
        return obj.qty < reorder

    class Meta:
        model = ItemInventory
        fields = "__all__"

class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = "__all__"

class HarvestLotSerializer(serializers.ModelSerializer):
    class Meta:
        model = HarvestLot
        fields = "__all__"

# Alias for HarvestLog if used interchangeably
HarvestLogSerializer = HarvestLotSerializer

class MaterialCatalogSerializer(serializers.Serializer):
    # Placeholder for missing serializer from legacy
    pass

class HarvestProductCatalogSerializer(serializers.Serializer):
    # Placeholder
    pass

class HarvestProductFarmStatsSerializer(serializers.Serializer):
    # Placeholder
    pass

from smart_agri.inventory.models import PurchaseOrder, PurchaseOrderItem

class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)
    
    class Meta:
        from smart_agri.inventory.models import PurchaseOrderItem
        model = PurchaseOrderItem
        fields = '__all__'

class PurchaseOrderSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True, read_only=True)
    vendor_name = serializers.CharField(required=True)
    
    class Meta:
        from smart_agri.inventory.models import PurchaseOrder
        model = PurchaseOrder
        fields = '__all__'
        read_only_fields = ['total_amount', 'status']

class BiologicalAssetCohortSerializer(serializers.ModelSerializer):
    variety_name = serializers.CharField(source='variety.name', read_only=True)
    crop_name = serializers.CharField(source='crop.name', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    parent_cohort_batch = serializers.CharField(source='parent_cohort.batch_name', read_only=True)

    class Meta:
        from smart_agri.core.models.inventory import BiologicalAssetCohort
        model = BiologicalAssetCohort
        fields = '__all__'

class BiologicalAssetTransactionSerializer(serializers.ModelSerializer):
    cohort_batch = serializers.CharField(source='cohort.batch_name', read_only=True)
    
    class Meta:
        from smart_agri.core.models.inventory import BiologicalAssetTransaction
        model = BiologicalAssetTransaction
        fields = '__all__'

class TreeCensusVarianceAlertSerializer(serializers.ModelSerializer):
    farm_name = serializers.CharField(source='farm.name', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    crop_name = serializers.CharField(source='crop.name', read_only=True)
    log_date = serializers.DateField(source='log.log_date', read_only=True)
    resolved_by_name = serializers.CharField(source='resolved_by.username', read_only=True)
    cohort_name = serializers.SerializerMethodField()

    class Meta:
        from smart_agri.core.models.inventory import TreeCensusVarianceAlert
        model = TreeCensusVarianceAlert
        fields = '__all__'

    def get_cohort_name(self, obj):
        if obj.cohort:
            return str(obj.cohort)
        return None

from decimal import Decimal

# --- [Axis 18] Mass Casualty Write-off Serializers ---

class MassCasualtyCohortEntrySerializer(serializers.Serializer):
    cohort_id = serializers.IntegerField()
    quantity_lost = serializers.IntegerField(min_value=1)
    estimated_fair_value_per_unit = serializers.DecimalField(max_digits=19, decimal_places=4, min_value=Decimal("0.0"))

class MassCasualtyWriteoffRequestSerializer(serializers.Serializer):
    farm_id = serializers.IntegerField()
    cause = serializers.ChoiceField(choices=[
        ('FROST', 'Frost/صقيع'),
        ('DISEASE', 'Disease/مرض'),
        ('FLOOD', 'Flood/فيضان'),
        ('FIRE', 'Fire/حريق'),
        ('OTHER', 'Other/أخرى'),
    ])
    reason = serializers.CharField(min_length=10)
    cohort_entries = MassCasualtyCohortEntrySerializer(many=True)
    approved_by_manager_id = serializers.IntegerField()
    approved_by_auditor_id = serializers.IntegerField(required=False, allow_null=True)
    idempotency_key = serializers.CharField(max_length=100)
