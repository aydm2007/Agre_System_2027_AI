from django.db import models
from smart_agri.core.models.base import SoftDeleteModel
from smart_agri.core.models.farm import Farm
from smart_agri.inventory.models import Item
from smart_agri.sales.models import Customer

class POSSession(SoftDeleteModel):
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="pos_sessions")
    session_id = models.CharField(max_length=50, unique=True)
    device_id = models.CharField(max_length=100)  # For Offline Sync Tracking
    opened_by = models.CharField(max_length=100)
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    closing_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    offline_data = models.JSONField(default=dict, blank=True)  # Temp storage for unsynced transactions
    payment_account_code = models.CharField(max_length=50, default='1100-CASH')
    
    class Meta:
        verbose_name = "جلسة بيع (POS Session)"
        verbose_name_plural = "جلسات البيع"
        indexes = [models.Index(fields=['device_id', 'is_active'])]

class POSOrder(SoftDeleteModel):
    session = models.ForeignKey(POSSession, on_delete=models.CASCADE, related_name="orders")
    order_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    order_date = models.DateTimeField(auto_now_add=True)
    device_timestamp = models.DateTimeField()  # Client-side actual time
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=20, choices=[
        ('cash', 'نقدي'), ('card', 'بطاقة'), ('credit', 'آجل')
    ])
    is_synced = models.BooleanField(default=False)
    sync_error = models.TextField(blank=True)
    
    # [AXIS 20] Forensic Evidence & GPS Verification
    latitude = models.DecimalField(max_digits=12, decimal_places=9, null=True, blank=True)
    longitude = models.DecimalField(max_digits=12, decimal_places=9, null=True, blank=True)
    accuracy = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    idempotency_key = models.CharField(max_length=100, unique=True, null=True, blank=True)
    
    class Meta:
        verbose_name = "طلب بيع (POS Order)"
        verbose_name_plural = "طلبات البيع"
    
class POSOrderLine(SoftDeleteModel):
    order = models.ForeignKey(POSOrder, on_delete=models.CASCADE, related_name='lines')
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)
