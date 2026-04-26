from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import SalesInvoice, SalesInvoiceItem
from smart_agri.core.models import StockMovement

# @receiver(post_save, sender=SalesInvoice)
# def manage_sale_inventory(sender, instance, created, **kwargs):
#     """
#     [DEPRECATED/DISABLED] by Forensic Remediation.
#     This signal caused O(N^2) DB operations and race conditions.
#     Logic has been moved to SaleService.confirm_sale().
#     """
#     pass
