import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from smart_agri.core.models.procurement import RequestForQuotation, SupplierQuotation, RFQStatus
from smart_agri.inventory.models import PurchaseOrder, PurchaseOrderItem
from smart_agri.core.models.farm import Farm

logger = logging.getLogger(__name__)

class ProcurementService:
    def __init__(self, farm: Farm):
        self.farm = farm

    @transaction.atomic
    def issue_rfq(self, rfq: RequestForQuotation):
        """إرسال طلب عروض الأسعار"""
        if rfq.status != RFQStatus.DRAFT:
            raise ValidationError("يمكن إرسال المسودات فقط.")
        
        if not rfq.lines.exists():
            raise ValidationError("لا يمكن إرسال طلب عروض أسعار بدون بنود.")
            
        rfq.status = RFQStatus.ISSUED
        rfq.issue_date = timezone.now().date()
        rfq.save()
        logger.info(f"RFQ {rfq.rfq_number} issued for farm {self.farm.id}")

    @transaction.atomic
    def award_rfq(self, rfq: RequestForQuotation, quotation_id: int):
        """ترسية المناقصة وإنشاء أمر الشراء"""
        quotation = SupplierQuotation.objects.get(pk=quotation_id, rfq=rfq)
        
        if rfq.status == RFQStatus.AWARDED:
            raise ValidationError("تمت ترسية هذه المناقصة سابقاً.")

        # 1. تحديث المناقصة والعرض
        quotation.is_awarded = True
        quotation.save()
        
        rfq.status = RFQStatus.AWARDED
        rfq.save()
        
        # 2. إنشاء أمر الشراء (Purchase Order) آلياً
        po = PurchaseOrder.objects.create(
            farm=self.farm,
            vendor_name=quotation.supplier.name,
            order_date=timezone.now().date(),
            status=PurchaseOrder.Status.DRAFT,
            total_amount=quotation.total_amount,
            notes=f"تم الإنشاء آلياً من المناقصة رقم: {rfq.rfq_number}"
        )
        
        for q_line in quotation.lines.all():
            PurchaseOrderItem.objects.create(
                purchase_order=po,
                item=q_line.rfq_line.item,
                qty=q_line.rfq_line.quantity,
                unit_price=q_line.unit_price
            )
            
        logger.info(f"RFQ {rfq.rfq_number} awarded to {quotation.supplier.name}. PO {po.id} created.")
        return po
