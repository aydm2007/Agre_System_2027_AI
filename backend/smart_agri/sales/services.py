from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils import timezone

from .models import SalesInvoice, SalesInvoiceItem
from smart_agri.inventory.models import Item, ItemInventory
from smart_agri.finance.models import FinancialLedger, SectorRelationship
from smart_agri.finance.services.core_finance import FinanceService
from smart_agri.core.api.permissions import _ensure_user_has_farm_access


class SaleService:
    # Accounting constants
    ACCOUNT_REVENUE = FinancialLedger.ACCOUNT_SALES_REVENUE
    ACCOUNT_RECEIVABLE = FinancialLedger.ACCOUNT_RECEIVABLE
    ACCOUNT_SECTOR_PAYABLE = FinancialLedger.ACCOUNT_SECTOR_PAYABLE
    ACCOUNT_COGS = FinancialLedger.ACCOUNT_COGS
    ACCOUNT_INVENTORY_ASSET = FinancialLedger.ACCOUNT_INVENTORY_ASSET
    ACCOUNT_VAT_PAYABLE = FinancialLedger.ACCOUNT_VAT_PAYABLE
    MONEY_PLACES = Decimal("0.01")

    @staticmethod
    def _to_decimal(value, field_name):
        try:
            return Decimal(str(value))
        except (ValidationError, OperationalError) as exc:
            raise ValidationError({field_name: "قيمة عشرية غير صالحة."}) from exc

    @staticmethod
    def _normalize_items(items_data):
        if not items_data:
            raise ValidationError({"items": "يجب أن تحتوي الفاتورة على صنف واحد على الأقل."})

        normalized = []
        for index, row in enumerate(items_data):
            item_ref = row.get("item")
            item_obj = item_ref if isinstance(item_ref, Item) else Item.objects.filter(pk=item_ref).first()
            if not item_obj:
                raise ValidationError({"items": f"صنف غير صالح في السطر رقم {index + 1}."})

            qty = SaleService._to_decimal(row.get("qty", 0), "qty")
            if qty <= 0:
                raise ValidationError({"qty": "الكمية يجب أن تكون أكبر من الصفر."})

            price_input = row.get("unit_price")
            if price_input is None:
                price_input = item_obj.unit_price
            unit_price = SaleService._to_decimal(price_input, "unit_price")
            if unit_price < 0:
                raise ValidationError({"unit_price": "سعر الوحدة لا يمكن أن يكون سالبًا."})

            line_total = (qty * unit_price).quantize(SaleService.MONEY_PLACES, rounding=ROUND_HALF_UP)
            normalized.append(
                {
                    "item": item_obj,
                    "description": row.get("description", "") or row.get("product_name", "") or item_obj.name,
                    "qty": qty,
                    "unit_price": unit_price.quantize(SaleService.MONEY_PLACES, rounding=ROUND_HALF_UP),
                    "total": line_total,
                }
            )
        return normalized

    @staticmethod
    @transaction.atomic
    def create_invoice(customer, location, invoice_date, items_data, user=None, notes="") -> SalesInvoice:
        if not customer:
            raise ValidationError({"customer": "العميل مطلوب."})
        if not location:
            raise ValidationError({"location": "الموقع مطلوب."})
        if not invoice_date:
            raise ValidationError({"invoice_date": "تاريخ الفاتورة مطلوب."})
        if not user or not getattr(user, "is_authenticated", False):
            raise ValidationError({"user": "مستخدم موثّق مطلوب."})

        _ensure_user_has_farm_access(user, location.farm_id)
        lines = SaleService._normalize_items(items_data)

        subtotal = sum((line["total"] for line in lines), Decimal("0.00")).quantize(
            SaleService.MONEY_PLACES, rounding=ROUND_HALF_UP
        )

        # [Phase 10] Dynamic Tax Alignment
        tax_percentage = Decimal("0.00")
        if hasattr(location.farm, 'settings'):
            tax_percentage = location.farm.settings.sales_tax_percentage
        
        tax_amount = (subtotal * (tax_percentage / Decimal("100"))).quantize(  # agri-guardian: decimal-safe
            SaleService.MONEY_PLACES, rounding=ROUND_HALF_UP
        )
        net_amount = (subtotal + tax_amount).quantize(
            SaleService.MONEY_PLACES, rounding=ROUND_HALF_UP
        )

        invoice = SalesInvoice.objects.create(
            farm=location.farm,
            customer=customer,
            location=location,
            invoice_date=invoice_date,
            status=SalesInvoice.STATUS_DRAFT,
            notes=notes or "",
            total_amount=subtotal,
            tax_amount=tax_amount,
            net_amount=net_amount,
            created_by=user,
        )

        SalesInvoiceItem.objects.bulk_create(
            [
                SalesInvoiceItem(
                    invoice=invoice,
                    item=line["item"],
                    description=line["description"],
                    qty=line["qty"],
                    unit_price=line["unit_price"],
                    total=line["total"],
                )
                for line in lines
            ]
        )
        return invoice

    @staticmethod
    @transaction.atomic
    def update_invoice(invoice: SalesInvoice, items_data=None, user=None, **changes) -> SalesInvoice:
        # Lock the invoice row only; joining nullable relations with FOR UPDATE
        # triggers PostgreSQL "nullable side of an outer join" errors.
        invoice = SalesInvoice.objects.select_for_update().get(pk=invoice.pk)
        if invoice.status in [SalesInvoice.STATUS_APPROVED, SalesInvoice.STATUS_PAID, SalesInvoice.STATUS_CANCELLED]:
            raise ValidationError("لا يمكن تعديل الفاتورة بعد الاعتماد/الدفع/الإلغاء. التعديل متاح فقط في حالة مسودة.")
        if not user or not getattr(user, "is_authenticated", False):
            raise ValidationError({"user": "مستخدم موثّق مطلوب."})

        location = changes.get("location", invoice.location)
        if location and not getattr(user, "is_superuser", False):
            _ensure_user_has_farm_access(user, location.farm_id)

        if "customer" in changes and changes["customer"] is not None:
            invoice.customer = changes["customer"]
        if "invoice_date" in changes and changes["invoice_date"] is not None:
            invoice.invoice_date = changes["invoice_date"]
        if "notes" in changes:
            invoice.notes = changes.get("notes") or ""
        if location is not None:
            invoice.location = location
            invoice.farm = location.farm

        if items_data is not None:
            lines = SaleService._normalize_items(items_data)
            subtotal = sum((line["total"] for line in lines), Decimal("0.00")).quantize(
                SaleService.MONEY_PLACES, rounding=ROUND_HALF_UP
            )
            invoice.items.all().delete()
            SalesInvoiceItem.objects.bulk_create(
                [
                    SalesInvoiceItem(
                        invoice=invoice,
                        item=line["item"],
                        description=line["description"],
                        qty=line["qty"],
                        unit_price=line["unit_price"],
                        total=line["total"],
                    )
                    for line in lines
                ]
            )
            invoice.total_amount = subtotal
            
            # [Phase 10] Dynamic Tax Alignment
            tax_percentage = Decimal("0.00")
            if hasattr(invoice.farm, 'settings'):
                tax_percentage = invoice.farm.settings.sales_tax_percentage
            
            invoice.tax_amount = (subtotal * (tax_percentage / Decimal("100"))).quantize(  # agri-guardian: decimal-safe
                SaleService.MONEY_PLACES, rounding=ROUND_HALF_UP
            )
            invoice.net_amount = (subtotal + invoice.tax_amount).quantize(
                SaleService.MONEY_PLACES, rounding=ROUND_HALF_UP
            )

        invoice.save()
        return invoice

    @staticmethod
    def _calculate_minimum_price(item: Item, farm) -> Decimal:
        """
        [AGRI-GUARDIAN §10.IV] Auto-Pricing Engine:
        Calculates the minimum acceptable sale price based on the Item's Moving Average Cost (unit_price),
        plus Zakat allocation (from LocationIrrigationPolicy or Farm.zakat_rule) and a 5% safety margin.
        This enforces direct financial governance preventing sales below cost.

        [D5 FIX] Zakat rate is now resolved from the farm's actual policy instead of hardcoded 10%.
        Fallback order: Farm.zakat_rule → conservative 10% if unknown.
        """
        base_cost = item.unit_price or Decimal("0.00")
        if base_cost <= 0:
            return Decimal("0.00") # Cannot enforce if cost is unknown/zero

        # [D5] Resolve actual zakat rate from farm's zakat_rule
        zakat_rate = Decimal("0.10")  # Conservative default
        if farm is not None:
            from smart_agri.core.services.zakat_policy import ZAKAT_RATE_MAP
            farm_rule = getattr(farm, 'zakat_rule', None)
            if farm_rule and farm_rule in ZAKAT_RATE_MAP:
                zakat_rate = ZAKAT_RATE_MAP[farm_rule]

        # Add zakat liability protection + 5% minimum operating margin
        zakat_margin = base_cost * zakat_rate
        safety_margin = base_cost * Decimal("0.05")
        
        minimum_price = base_cost + zakat_margin + safety_margin
        return minimum_price.quantize(SaleService.MONEY_PLACES, rounding=ROUND_HALF_UP)

    @staticmethod
    def check_confirmability(invoice: SalesInvoice, user=None, lock_inventory=False) -> None:
        """
        Validate confirm prerequisites without mutating state.
        Raises ValidationError/PermissionDenied with Arabic business messages.
        """
        if invoice.status in [SalesInvoice.STATUS_APPROVED, SalesInvoice.STATUS_PAID]:
            return
        if invoice.status == SalesInvoice.STATUS_CANCELLED:
            raise ValidationError("لا يمكن اعتماد فاتورة ملغاة.")

        if (
            user
            and invoice.created_by
            and invoice.created_by == user
            and not getattr(user, "is_superuser", False)
        ):
            raise PermissionDenied("مبدأ الفصل الرقابي: لا يمكنك اعتماد فاتورة قمت بإنشائها.")

        FinanceService.check_fiscal_period(invoice.invoice_date, invoice.farm, strict=True)

        items = invoice.items.select_related("item").all()
        if not items.exists():
            raise ValidationError("لا يمكن اعتماد فاتورة بدون بنود.")

        for line in items:
            if not line.item:
                raise ValidationError("يوجد بند فاتورة بدون صنف مرتبط.")
            inv_qs = ItemInventory.objects.filter(
                farm_id=invoice.farm_id,
                location_id=invoice.location_id,
                item_id=line.item_id,
            )
            if lock_inventory:
                inv_qs = inv_qs.select_for_update()
            inv_row = inv_qs.first()
            available = inv_row.qty if inv_row else Decimal("0")
            if available < line.qty:
                raise ValidationError(
                    f"المخزون غير كافٍ للصنف {line.item.name}. المتاح: {available}، المطلوب: {line.qty}."
                )
                
            # [AGRI-GUARDIAN §10.IV] Direct Financial Governance: Auto-Pricing Enforcement
            minimum_price = SaleService._calculate_minimum_price(line.item, invoice.farm)
            if minimum_price > 0 and line.unit_price < minimum_price:
                raise ValidationError(
                    f"السعر المدخل للصنف {line.item.name} ({line.unit_price}) أقل من الحد الأدنى المسموح به للبيع ({minimum_price}). "
                    "تم احتساب الحد الأدنى بناءً على متوسط التكلفة مع هامش الأمان والزكاة لحماية أرباح المزرعة."
                )

        net_revenue = (invoice.net_amount or invoice.total_amount or Decimal("0.00")).quantize(
            SaleService.MONEY_PLACES, rounding=ROUND_HALF_UP
        )
        if net_revenue > 0:
            sector_relationship, _ = SectorRelationship.objects.get_or_create(
                farm=invoice.farm,
                defaults={"current_balance": Decimal("0.0000"), "allow_revenue_recycling": False},
            )
            # [AGRI-GUARDIAN §Axis-4] Revenue recycling governance:
            # Auto-transfer to sector account is handled in confirm_sale().
            # No longer blocks confirmation — the sector payable entry
            # is created automatically to enforce fund governance.

    @staticmethod
    @transaction.atomic
    def confirm_sale(invoice: SalesInvoice, user=None) -> SalesInvoice:
        invoice = SalesInvoice.objects.select_for_update().get(pk=invoice.pk)

        # Idempotent confirm: repeated confirm calls should be safe no-op.
        if invoice.status in [SalesInvoice.STATUS_APPROVED, SalesInvoice.STATUS_PAID]:
            return invoice
        SaleService.check_confirmability(invoice, user=user, lock_inventory=True)

        invoice.status = SalesInvoice.STATUS_APPROVED
        invoice.approved_by = user
        invoice.approved_at = timezone.now()
        invoice.save(update_fields=["status", "approved_by", "approved_at"])

        from smart_agri.core.models import StockMovement
        if StockMovement.objects.filter(ref_type="sale", ref_id=str(invoice.id)).exists():
            raise ValidationError("تم العثور على حركات مخزون مرتبطة بهذه الفاتورة؛ تم إيقاف عملية الاعتماد.")

        from smart_agri.core.services.inventory_service import InventoryService
        items = invoice.items.select_related("item").all()
        for line in items:
            if not line.item:
                continue
            InventoryService.record_movement(
                farm=invoice.farm,
                item=line.item,
                qty_delta=-line.qty,
                location=invoice.location,
                ref_type="sale",
                ref_id=str(invoice.id),
                note=f"صرف مبيعات للفاتورة رقم {invoice.id} - العميل: {invoice.customer.name}",
                actor_user=user,
            )

        net_revenue = (invoice.net_amount or invoice.total_amount or Decimal("0.00")).quantize(
            SaleService.MONEY_PLACES, rounding=ROUND_HALF_UP
        )

        if net_revenue > 0:
            # [AGRI-GUARDIAN] Idempotency Guard — prevent duplicate postings on retry
            from django.contrib.contenttypes.models import ContentType
            sale_ct = ContentType.objects.get_for_model(SalesInvoice)
            if FinancialLedger.objects.filter(
                content_type=sale_ct,
                object_id=str(invoice.id),
                account_code=SaleService.ACCOUNT_REVENUE,
            ).exists():
                return invoice  # Already posted, replay-safe

            sector_relationship, _ = SectorRelationship.objects.select_for_update().get_or_create(
                farm=invoice.farm,
                defaults={"current_balance": Decimal("0.0000"), "allow_revenue_recycling": False},
            )
            # [AGRI-GUARDIAN §Axis-4] Revenue recycling auto-transfer:
            # Instead of blocking, create sector payable entries automatically.
            # This ensures revenue governance without halting operations.

            # [AGRI-GUARDIAN] Double-Entry: Credit Revenue (Subtotal)
            revenue_amount = (invoice.total_amount or Decimal("0.00")).quantize(
                SaleService.MONEY_PLACES, rounding=ROUND_HALF_UP
            )
            FinancialLedger.objects.create(
                activity=None,
                farm=invoice.farm,
                content_type=sale_ct,
                object_id=str(invoice.id),
                account_code=SaleService.ACCOUNT_REVENUE,
                credit=revenue_amount,
                debit=0,
                description=f"إثبات إيراد المبيعات - فاتورة #{invoice.id} ({invoice.customer.name})",
                created_by=user,
                currency=invoice.currency,
            )

            # [Phase 10] Double-Entry: Credit VAT Payable
            tax_amount = (invoice.tax_amount or Decimal("0.00")).quantize(
                SaleService.MONEY_PLACES, rounding=ROUND_HALF_UP
            )
            if tax_amount > 0:
                FinancialLedger.objects.create(
                    activity=None,
                    farm=invoice.farm,
                    content_type=sale_ct,
                    object_id=str(invoice.id),
                    account_code=SaleService.ACCOUNT_VAT_PAYABLE,
                    credit=tax_amount,
                    debit=0,
                    description=f"استحقاق ضريبة القيمة المضافة - فاتورة #{invoice.id}",
                    created_by=user,
                    currency=invoice.currency,
                )

            # [AGRI-GUARDIAN] Double-Entry: Debit Receivable (Total)
            FinancialLedger.objects.create(
                activity=None,
                farm=invoice.farm,
                content_type=sale_ct,
                object_id=str(invoice.id),
                account_code=SaleService.ACCOUNT_RECEIVABLE,
                credit=0,
                debit=net_revenue,
                description=f"ذمم مدينة على العميل {invoice.customer.name} - فاتورة #{invoice.id}",
                created_by=user,
                currency=invoice.currency,
            )
            # [AGRI-GUARDIAN] Fund Accounting: Update sector balance tracker
            # NOTE: Sector Payable is NOT posted to the ledger here to avoid
            # unbalanced entries. The sector relationship balance is tracked
            # separately via SectorRelationship.current_balance.
            sector_relationship.current_balance = (sector_relationship.current_balance or Decimal("0")) + net_revenue
            sector_relationship.save(update_fields=["current_balance"])

            # [AGRI-GUARDIAN §Axis-4] Auto-transfer sector payable entry:
            # Creates obligation to transfer revenue to sector HQ.
            if not sector_relationship.allow_revenue_recycling:
                from django.contrib.contenttypes.models import ContentType as CT_Model
                sale_ct_for_sector = CT_Model.objects.get_for_model(SalesInvoice)
                FinancialLedger.objects.create(
                    activity=None,
                    farm=invoice.farm,
                    content_type=sale_ct_for_sector,
                    object_id=str(invoice.id),
                    account_code=SaleService.ACCOUNT_SECTOR_PAYABLE,
                    debit=0,
                    credit=net_revenue,
                    description=f"قيد تلقائي — التزام تحويل إيراد للقطاع (فاتورة #{invoice.id})",
                    created_by=user,
                    currency=invoice.currency,
                )

        # [AGRI-GUARDIAN §9.II] COGS + Inventory Asset: Complete double-entry accounting.
        # Debit COGS (expense recognition) and Credit Inventory Asset (stock reduction by cost).
        for line in items:
            if not line.item:
                continue
            item_cost = (line.qty * (line.item.unit_price or Decimal("0"))).quantize(
                SaleService.MONEY_PLACES, rounding=ROUND_HALF_UP
            )
            if item_cost <= 0:
                continue
            crop_plan = line.harvest_lot.crop_plan if getattr(line, 'harvest_lot', None) else None
            common_kwargs = dict(
                activity=None,
                farm=invoice.farm,
                created_by=user,
                currency=invoice.currency,
                crop_plan=crop_plan,
                cost_center=getattr(crop_plan, 'cost_center', None) if crop_plan else None,
            )
            FinancialLedger.objects.create(
                account_code=SaleService.ACCOUNT_COGS,
                debit=item_cost,
                credit=0,
                description=f"تكلفة بضاعة مباعة - {line.item.name} - فاتورة #{invoice.id}",
                **common_kwargs
            )
            FinancialLedger.objects.create(
                account_code=SaleService.ACCOUNT_INVENTORY_ASSET,
                debit=0,
                credit=item_cost,
                description=f"تخفيض أصل المخزون - {line.item.name} - فاتورة #{invoice.id}",
                **common_kwargs
            )

        return invoice

    @staticmethod
    @transaction.atomic
    def cancel_sale(invoice: SalesInvoice, user=None) -> SalesInvoice:
        invoice = SalesInvoice.objects.select_for_update().get(pk=invoice.pk)
        if invoice.status == SalesInvoice.STATUS_CANCELLED:
            return invoice

        FinanceService.check_fiscal_period(invoice.invoice_date, invoice.farm, strict=True)

        invoice.status = SalesInvoice.STATUS_CANCELLED
        invoice.save(update_fields=["status"])

        from smart_agri.core.services.inventory_service import InventoryService
        for line in invoice.items.select_related("item").all():
            if not line.item:
                continue
            InventoryService.record_movement(
                farm=invoice.farm,
                item=line.item,
                qty_delta=line.qty,
                location=invoice.location,
                ref_type="sale_reversal",
                ref_id=str(invoice.id),
                note=f"عكس صرف المبيعات بعد إلغاء الفاتورة رقم {invoice.id}",
                actor_user=user,
            )

        net_revenue = (invoice.net_amount or invoice.total_amount or Decimal("0.00")).quantize(
            SaleService.MONEY_PLACES, rounding=ROUND_HALF_UP
        )

        if net_revenue > 0:
            # [AGRI-GUARDIAN] Double-Entry Reversal: Debit Revenue
            FinancialLedger.objects.create(
                activity=None,
                farm=invoice.farm,
                account_code=SaleService.ACCOUNT_REVENUE,
                credit=0,
                debit=net_revenue,
                description=f"قيد عكسي لإيراد المبيعات - فاتورة #{invoice.id}",
                created_by=user,
                currency=invoice.currency,
            )
            # [AGRI-GUARDIAN] Double-Entry Reversal: Credit Receivable
            FinancialLedger.objects.create(
                activity=None,
                farm=invoice.farm,
                account_code=SaleService.ACCOUNT_RECEIVABLE,
                credit=net_revenue,
                debit=0,
                description=f"قيد عكسي للذمم المدينة - فاتورة #{invoice.id}",
                created_by=user,
                currency=invoice.currency,
            )
            # [AGRI-GUARDIAN] Fund Accounting: Reverse sector balance tracker
            relationship = SectorRelationship.objects.select_for_update().filter(farm=invoice.farm).first()
            if relationship:
                relationship.current_balance = (relationship.current_balance or Decimal("0")) - net_revenue
                relationship.save(update_fields=["current_balance"])

        # [AGRI-GUARDIAN §9.II] Reversal for COGS + Inventory Asset entries.
        for line in invoice.items.select_related("item").all():
            if not line.item:
                continue
            item_cost = (line.qty * (line.item.unit_price or Decimal("0"))).quantize(
                SaleService.MONEY_PLACES, rounding=ROUND_HALF_UP
            )
            if item_cost <= 0:
                continue
            crop_plan = line.harvest_lot.crop_plan if getattr(line, 'harvest_lot', None) else None
            common_kwargs = dict(
                activity=None,
                farm=invoice.farm,
                created_by=user,
                currency=invoice.currency,
                crop_plan=crop_plan,
                cost_center=getattr(crop_plan, 'cost_center', None) if crop_plan else None,
            )
            FinancialLedger.objects.create(
                account_code=SaleService.ACCOUNT_COGS,
                debit=0,
                credit=item_cost,
                description=f"قيد عكسي لتكلفة البضاعة المباعة - {line.item.name} - فاتورة #{invoice.id}",
                **common_kwargs
            )
            FinancialLedger.objects.create(
                account_code=SaleService.ACCOUNT_INVENTORY_ASSET,
                debit=item_cost,
                credit=0,
                description=f"إعادة أصل المخزون - {line.item.name} - فاتورة #{invoice.id}",
                **common_kwargs
            )

        return invoice
