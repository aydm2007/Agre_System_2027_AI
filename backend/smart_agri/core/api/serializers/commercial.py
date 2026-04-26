from rest_framework import serializers
from django.db import transaction
from smart_agri.sales.models import Customer, SalesInvoice, SalesInvoiceItem
# from smart_agri.core.models.task import Task

# =============================================================================
# COMMERCIAL SERIALIZERS
# =============================================================================

# class ServiceProviderSerializer(serializers.ModelSerializer):
#     type_display = serializers.CharField(source='get_provider_type_display', read_only=True)
#     capabilities_names = serializers.StringRelatedField(many=True, source='capabilities', read_only=True)
#     capabilities = serializers.PrimaryKeyRelatedField(
#         many=True, 
#         queryset=Task.objects.all(),
#         required=False
#     )
# 
#     class Meta:
#         model = ServiceProvider  # Model is deleted
#         fields = [
#             'id', 'name', 'provider_type', 'type_display', 
#             'phone', 'address', 'tax_number', 'default_hourly_rate', 'notes',
#             'capabilities', 'capabilities_names'
#         ]
# 
#     def create(self, validated_data):
#         capabilities = validated_data.pop('capabilities', [])
#         instance = super().create(validated_data)
#         instance.capabilities.set(capabilities)
#         return instance
# 
#     def update(self, instance, validated_data):
#         capabilities = validated_data.pop('capabilities', None)
#         instance = super().update(instance, validated_data)
#         if capabilities is not None:
#             instance.capabilities.set(capabilities)
#         return instance

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'

class SalesInvoiceItemSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)
    
    class Meta:
        model = SalesInvoiceItem
        fields = ['id', 'item', 'item_name', 'description', 'qty', 'unit_price', 'total']
        read_only_fields = ['total']

class SalesInvoiceSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    items = SalesInvoiceItemSerializer(many=True, required=False)
    
    class Meta:
        model = SalesInvoice
        fields = '__all__'
        read_only_fields = ['created_by', 'approved_by', 'approved_at', 'total_amount', 'tax_amount', 'net_amount']

    def create(self, validated_data):
        """Delegate to SalesInvoiceService for proper service layer compliance."""
        from smart_agri.core.services.sales_invoice_service import SalesInvoiceService
        items_data = validated_data.pop('items', [])
        return SalesInvoiceService.create_invoice(validated_data, items_data)

    def update(self, instance, validated_data):
        """Delegate to SalesInvoiceService for proper service layer compliance."""
        from smart_agri.core.services.sales_invoice_service import SalesInvoiceService
        items_data = validated_data.pop('items', None)
        return SalesInvoiceService.update_invoice(instance, validated_data, items_data)

# =============================================================================
# ADDITIONAL SERIALIZERS (API Integration)
# These satisfy imports in __init__.py
# =============================================================================

class FinancialLedgerSerializer(serializers.Serializer):
    """Serializer for Financial Ledger read operations."""
    id = serializers.IntegerField(read_only=True)
    farm = serializers.IntegerField(source='farm_id', read_only=True)
    crop_plan = serializers.IntegerField(source='crop_plan_id', allow_null=True, read_only=True)
    activity = serializers.IntegerField(source='activity_id', allow_null=True, read_only=True)
    description = serializers.CharField(read_only=True)
    debit = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    credit = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    transaction_date = serializers.DateTimeField(read_only=True)
    currency = serializers.CharField(read_only=True)


class CostAllocationInputSerializer(serializers.Serializer):
    """Input serializer for cost allocation operations."""
    farm_id = serializers.IntegerField(required=True)
    period_start = serializers.DateField(required=True)
    period_end = serializers.DateField(required=True)


class HarvestGradingInputSerializer(serializers.Serializer):
    """Input serializer for harvest grading operations."""
    harvest_lot_id = serializers.IntegerField(required=True)
    grade = serializers.CharField(max_length=20, required=True)
    qty = serializers.DecimalField(max_digits=15, decimal_places=2, required=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class ProfitabilityReportSerializer(serializers.Serializer):
    """Serializer for profitability report output."""
    farm_id = serializers.IntegerField(read_only=True)
    farm_name = serializers.CharField(read_only=True)
    crop_plan_id = serializers.IntegerField(read_only=True)
    total_revenue = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    total_cost = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    net_profit = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    profit_margin = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    currency = serializers.CharField(read_only=True)

