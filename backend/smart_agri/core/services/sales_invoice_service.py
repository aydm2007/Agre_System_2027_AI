"""
Sales Invoice Service - DEPRECATED Legacy Service.

[AGRI-GUARDIAN] WARNING: This service is superseded by smart_agri.sales.services.SaleService
which provides full double-entry, idempotency, fiscal period checks, and separation of duties.
Do NOT use this service for new code paths.
"""
import warnings
from decimal import Decimal
from django.db import transaction
from django.conf import settings

from smart_agri.core.models.commercial import SalesInvoice, SalesInvoiceItem


class SalesInvoiceService:
    """
    DEPRECATED: Use smart_agri.sales.services.SaleService instead.
    This legacy service lacks fiscal period checks, idempotency, and double-entry compliance.
    """

    @staticmethod
    @transaction.atomic
    def create_invoice(validated_data: dict, items_data: list) -> SalesInvoice:
        """
        Create a new sales invoice with items.
        DEPRECATED: Use SaleService.create_invoice instead.
        """
        warnings.warn(
            "SalesInvoiceService.create_invoice is deprecated. "
            "Use smart_agri.sales.services.SaleService.create_invoice instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        invoice = SalesInvoice.objects.create(**validated_data)
        
        for item_data in items_data:
            SalesInvoiceItem.objects.create(invoice=invoice, **item_data)
        
        return invoice

    @staticmethod
    @transaction.atomic
    def update_invoice(instance: SalesInvoice, validated_data: dict, items_data: list = None) -> SalesInvoice:
        """
        Update an existing sales invoice.
        DEPRECATED: Use SaleService.update_invoice instead.
        """
        warnings.warn(
            "SalesInvoiceService.update_invoice is deprecated. "
            "Use smart_agri.sales.services.SaleService.update_invoice instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if items_data is not None:
            # Simple Replace Logic for Edit Mode (Draft only)
            instance.items.all().delete()
            for item_data in items_data:
                SalesInvoiceItem.objects.create(invoice=instance, **item_data)
        
        return instance

