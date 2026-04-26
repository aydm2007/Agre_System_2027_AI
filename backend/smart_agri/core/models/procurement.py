from django.db import models
from smart_agri.core.models.base import SoftDeleteModel
from smart_agri.core.models.farm import Farm
from smart_agri.inventory.models import Item
from smart_agri.core.models.hr import Employee

class RFQStatus(models.TextChoices):
    DRAFT = 'draft', 'مسودة'
    ISSUED = 'issued', 'تم الإرسال'
    CLOSED = 'closed', 'مغلق'
    AWARDED = 'awarded', 'تم الترسية'

class TenderType(models.TextChoices):
    OPEN = 'open', 'مناقصة عامة'
    RESTRICTED = 'restricted', 'مناقصة محدودة'
    DIRECT = 'direct', 'ترسية مباشرة'

class RequestForQuotation(SoftDeleteModel):
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="rfqs")
    rfq_number = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    tender_type = models.CharField(max_length=20, choices=TenderType.choices, default=TenderType.OPEN)
    status = models.CharField(max_length=20, choices=RFQStatus.choices, default=RFQStatus.DRAFT)
    issue_date = models.DateField(null=True, blank=True)
    closing_date = models.DateField(null=True, blank=True)
    delivery_location = models.CharField(max_length=255)
    terms_conditions = models.TextField(blank=True)
    created_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        verbose_name = "طلب عروض أسعار"
        verbose_name_plural = "طلبات عروض الأسعار"
        ordering = ['-created_at']

class RFQLine(SoftDeleteModel):
    rfq = models.ForeignKey(RequestForQuotation, on_delete=models.CASCADE, related_name='lines')
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    description = models.CharField(max_length=255, blank=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    uom = models.CharField(max_length=20)
    required_date = models.DateField(null=True, blank=True)
    
class SupplierQuotation(SoftDeleteModel):
    rfq = models.ForeignKey(RequestForQuotation, on_delete=models.CASCADE, related_name='quotations')
    supplier_name = models.CharField(max_length=200, help_text="اسم المورد أو كود الحساب")
    supplier_account_code = models.CharField(max_length=50, blank=True, null=True)
    quotation_number = models.CharField(max_length=50)
    submitted_date = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    is_awarded = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "عرض سعر مورد"
        verbose_name_plural = "عروض أسعار الموردين"
    
class SupplierQuotationLine(SoftDeleteModel):
    quotation = models.ForeignKey(SupplierQuotation, on_delete=models.CASCADE, related_name='lines')
    rfq_line = models.ForeignKey(RFQLine, on_delete=models.CASCADE)
    unit_price = models.DecimalField(max_digits=15, decimal_places=2)
    delivery_days = models.IntegerField(default=0)
