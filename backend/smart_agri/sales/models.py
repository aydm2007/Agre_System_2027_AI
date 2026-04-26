
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from smart_agri.core.models.base import SoftDeleteModel

class Customer(SoftDeleteModel):
    def __init__(self, *args, **kwargs):
        kwargs.pop("farm", None)
        super().__init__(*args, **kwargs)

    TYPE_WHOLESALER = 'wholesaler'
    TYPE_RETAILER = 'retailer'
    TYPE_INDIVIDUAL = 'individual'
    TYPE_CHOICES = [
        (TYPE_WHOLESALER, 'تاجر جملة'),
        (TYPE_RETAILER, 'تاجر تجزئة'),
        (TYPE_INDIVIDUAL, 'فرد'),
    ]
    name = models.CharField(max_length=255, verbose_name="اسم العميل")
    customer_type = models.CharField(max_length=50, choices=TYPE_CHOICES, default=TYPE_INDIVIDUAL, verbose_name="نوع العميل")
    phone = models.CharField(max_length=50, blank=True, null=True, verbose_name="رقم الهاتف")
    address = models.TextField(blank=True, null=True, verbose_name="العنوان")
    tax_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="الرقم الضريبي")
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات")

    class Meta:
        db_table = 'core_customer'
        managed = True
        verbose_name = "عميل"
        verbose_name_plural = "العملاء"
    
    def __str__(self):
        return self.name

class SalesInvoice(SoftDeleteModel):
    def __init__(self, *args, **kwargs):
        legacy_sale_date = kwargs.pop("sale_date", None)
        if legacy_sale_date and "invoice_date" not in kwargs:
            kwargs["invoice_date"] = legacy_sale_date
        # Avoid injecting kwargs during ORM row hydration (positional args are used there).
        if not args and "invoice_date" not in kwargs:
            kwargs["invoice_date"] = timezone.localdate()
        super().__init__(*args, **kwargs)

    STATUS_DRAFT = 'draft'
    STATUS_APPROVED = 'approved'
    STATUS_PAID = 'paid'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'مسودة'),
        (STATUS_APPROVED, 'معتمد'),
        (STATUS_PAID, 'مدفوع'),
        (STATUS_CANCELLED, 'ملغي'),
    ]
    
    # [Agri-Guardian]: Re-instating farm link for proper isolation
    farm = models.ForeignKey('core.Farm', on_delete=models.CASCADE, related_name='sales_invoices_salesapp', null=True, blank=True)
    
    # Normalized Location
    location = models.ForeignKey('core.Location', on_delete=models.PROTECT, related_name='sales_invoices_salesapp', verbose_name="الموقع (المصدر)", null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='invoices', verbose_name="العميل")
    
    # Mapped legacy 'sale_date' to 'invoice_date' to support existing data if any, 
    # OR let migration rename it. We prefer clean schema name 'invoice_date'.
    invoice_date = models.DateField(verbose_name="تاريخ الفاتورة") 
    due_date = models.DateField(null=True, blank=True, verbose_name="تاريخ الاستحقاق")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, verbose_name="الحالة")
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات")
    
    # Financials
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name="الإجمالي")
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name="الضريبة")
    net_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name="الصافي")
    currency = models.CharField(max_length=10, default="YER", verbose_name="العملة")
    
    created_by = models.ForeignKey('auth.User', on_delete=models.PROTECT, related_name='created_invoices_salesapp')
    approved_by = models.ForeignKey('auth.User', on_delete=models.PROTECT, null=True, blank=True, related_name='approved_invoices_salesapp')
    approved_at = models.DateTimeField(null=True, blank=True)

    # [AGRI-GUARDIAN §11.III] Network Idempotency: Prevent duplicate invoice creation on flaky networks.
    idempotency_key = models.UUIDField(
        null=True, blank=True, unique=True,
        help_text="مفتاح عدم التكرار لمنع ازدواج الفواتير عند ضعف الشبكة"
    )

    class Meta:
        db_table = 'core_sales_invoice' 
        managed = True
        verbose_name = "فاتورة مبيعات"
        verbose_name_plural = "فواتير المبيعات"
        permissions = [
            ("approve_salesinvoice", "يمكن اعتماد فاتورة المبيعات"),
        ]

    @property
    def invoice_number(self):
        return str(self.id)

    def save(self, *args, **kwargs):
        if not self.created_by_id:
            user = self.approved_by
            if user is None:
                user_model = get_user_model()
                user = user_model.objects.filter(username="system_approver").first()
                if user is None:
                    user = user_model.objects.create_user(username="system_approver")
            if user is not None:
                self.created_by = user
        super().save(*args, **kwargs)


class SalesInvoiceItem(models.Model):
    invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE, related_name='items')
    # Use inventory app for Item lookup
    item = models.ForeignKey('inventory.Item', on_delete=models.PROTECT, verbose_name="الصنف")
    description = models.CharField(max_length=255, blank=True, verbose_name="الوصف")
    qty = models.DecimalField(max_digits=12, decimal_places=3, verbose_name="الكمية")
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="سعر الوحدة")
    total = models.DecimalField(max_digits=14, decimal_places=2, verbose_name="الإجمالي")

    # [AGRI-GUARDIAN §9.IV] Lifecycle Traceability: Seed-to-Sale chain of custody.
    # Every SalesInvoice item MUST be traceable back to a HarvestLot and CropPlan.
    harvest_lot = models.ForeignKey(
        'core.HarvestLot', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='sale_items',
        verbose_name="دفعة الحصاد"
    )
    batch_number = models.CharField(
        max_length=100, blank=True, null=True,
        verbose_name="رقم الدفعة",
        help_text="رقم الدفعة للتتبع الكامل من البذرة إلى البيع"
    )

    class Meta:
        db_table = 'core_sales_invoice_item'
        managed = True
        verbose_name = "عنصر الفاتورة"
        verbose_name_plural = "عناصر الفواتير"

    def save(self, *args, **kwargs):
        if self.total is None:
            self.total = (self.qty or 0) * (self.unit_price or 0)
        super().save(*args, **kwargs)
