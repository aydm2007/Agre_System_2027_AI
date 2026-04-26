from decimal import Decimal, ROUND_HALF_UP
import logging

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


class SalesService:
    """Unified Sales service: invoice approval -> inventory + ledger posting."""

    @staticmethod
    @transaction.atomic
    def approve_invoice(invoice: "smart_agri.sales.models.SalesInvoice", user):
        from smart_agri.core.services.inventory_service import InventoryService
        from smart_agri.finance.models import FinancialLedger
        from smart_agri.sales.models import SalesInvoice

        if invoice.status != SalesInvoice.STATUS_DRAFT:
            raise ValidationError(f"لا يمكن اعتماد الفاتورة وهي في الحالة: {invoice.status}")
        if not invoice.items.exists():
            raise ValidationError("لا يمكن اعتماد فاتورة بدون أصناف.")
        if invoice.created_by == user:
            raise PermissionDenied("مبدأ الفصل الرقابي: لا يمكنك اعتماد فاتورتك الخاصة.")
        if not invoice.location:
            raise ValidationError("يجب تحديد موقع المصدر للفاتورة.")

        total_cogs = Decimal("0")
        total_revenue = Decimal("0")
        precision = Decimal("0.0001")

        for line in invoice.items.select_related("item").all():
            item = line.item
            qty = line.qty

            line_cogs = (item.unit_price * qty).quantize(precision, rounding=ROUND_HALF_UP)
            line_revenue = (line.unit_price * qty).quantize(precision, rounding=ROUND_HALF_UP)
            total_cogs += line_cogs
            total_revenue += line_revenue

            InventoryService.record_movement(
                farm=invoice.farm,
                item=item,
                qty_delta=-qty,
                location=invoice.location,
                ref_type="SALES_INVOICE",
                ref_id=str(invoice.id),
                note=f"Sales invoice {invoice.id} for {invoice.customer.name}",
            )

        total_cogs = total_cogs.quantize(precision, rounding=ROUND_HALF_UP)
        total_revenue = total_revenue.quantize(precision, rounding=ROUND_HALF_UP)

        if total_revenue > 0:
            FinancialLedger.objects.create(
                account_code=FinancialLedger.ACCOUNT_RECEIVABLE,
                debit=total_revenue,
                credit=0,
                description=f"ذمم مدينة - فاتورة رقم {invoice.id}",
                created_by=user,
                currency=invoice.currency,
                farm=invoice.farm,
                cost_center=getattr(invoice.farm, 'cost_center', None),
            )
            FinancialLedger.objects.create(
                account_code=FinancialLedger.ACCOUNT_SECTOR_PAYABLE,
                debit=0,
                credit=total_revenue,
                description=f"مستحق تحويل لحساب القطاع الإنتاجي - فاتورة رقم {invoice.id}",
                created_by=user,
                currency=invoice.currency,
                farm=invoice.farm,
                cost_center=getattr(invoice.farm, 'cost_center', None),
            )
            # Compatibility reclassification for legacy reports expecting ACCOUNT_SALES_REVENUE.
            FinancialLedger.objects.create(
                account_code=FinancialLedger.ACCOUNT_SECTOR_PAYABLE,
                debit=total_revenue,
                credit=0,
                description=f"قيد عكسي لإيراد المبيعات (مدين) - فاتورة {invoice.id}",
                created_by=user,
                currency=invoice.currency,
                farm=invoice.farm,
                cost_center=getattr(invoice.farm, 'cost_center', None),
            )
            FinancialLedger.objects.create(
                account_code=FinancialLedger.ACCOUNT_SALES_REVENUE,
                debit=0,
                credit=total_revenue,
                description=f"إثبات إيراد المبيعات (دائن) - فاتورة {invoice.id}",
                created_by=user,
                currency=invoice.currency,
                farm=invoice.farm,
                cost_center=getattr(invoice.farm, 'cost_center', None),
            )

        if total_cogs > 0:
            FinancialLedger.objects.create(
                account_code=FinancialLedger.ACCOUNT_COGS,
                debit=total_cogs,
                credit=0,
                description=f"تكلفة البضاعة المباعة - فاتورة رقم {invoice.id}",
                created_by=user,
                currency=invoice.currency,
                farm=invoice.farm,
                cost_center=getattr(invoice.farm, 'cost_center', None),
            )
            FinancialLedger.objects.create(
                account_code=FinancialLedger.ACCOUNT_INVENTORY_ASSET,
                debit=0,
                credit=total_cogs,
                description=f"تخفيض أصل المخزون - فاتورة رقم {invoice.id}",
                created_by=user,
                currency=invoice.currency,
                farm=invoice.farm,
                cost_center=getattr(invoice.farm, 'cost_center', None),
            )

        invoice.status = SalesInvoice.STATUS_APPROVED
        invoice.approved_by = user
        invoice.approved_at = timezone.now()
        invoice.save()

        logger.info(
            "Invoice %s approved. Revenue=%s COGS=%s",
            invoice.id,
            total_revenue,
            total_cogs,
        )
        return invoice
