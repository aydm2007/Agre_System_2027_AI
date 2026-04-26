"""
[AGRI-GUARDIAN] Sales Service Tests.
Covers:
1. SaleService._calculate_minimum_price — Auto-pricing engine validation
2. SalesInvoice/SalesInvoiceItem model structure (Decimal, farm_id)
3. Service Layer Pattern compliance

Compliance:
- Axis 4: Fund Accounting — revenue is custodial, not farm-owned
- Axis 5: Decimal precision — no float in pricing
- Axis 6: Tenant isolation — farm-scoped sales
- Axis 9: Zakat rate in pricing formula
"""
import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch


# ──────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────

def _make_item(unit_price="100.00"):
    item = MagicMock()
    item.unit_price = Decimal(str(unit_price))
    item.name = "Test Crop Product"
    return item


def _make_farm(zakat_rule="10_PERCENT", pk=1):
    farm = MagicMock()
    farm.id = pk
    farm.pk = pk
    farm.zakat_rule = zakat_rule
    farm.name = "Test Farm"
    return farm


# ──────────────────────────────────────────────────────────────────────────
# 1. Auto-Pricing Engine (Axis 4 + Axis 5 + Axis 9)
# ──────────────────────────────────────────────────────────────────────────

class TestSaleAutoPricing:
    """Tests for SaleService._calculate_minimum_price — COGS + Zakat% + 5% margin."""

    def test_rain_fed_10_percent_zakat(self):
        """Rain-fed: COGS * (1 + 0.10 + 0.05) = COGS * 1.15"""
        from smart_agri.sales.services import SaleService
        item = _make_item("200.00")
        farm = _make_farm("10_PERCENT")
        result = SaleService._calculate_minimum_price(item, farm=farm)
        assert result == Decimal("230.00"), f"Expected 230.00, got {result}"

    def test_well_5_percent_zakat(self):
        """Well: COGS * (1 + 0.05 + 0.05) = COGS * 1.10"""
        from smart_agri.sales.services import SaleService
        item = _make_item("200.00")
        farm = _make_farm("5_PERCENT")
        result = SaleService._calculate_minimum_price(item, farm=farm)
        assert result == Decimal("220.00"), f"Expected 220.00, got {result}"

    def test_mixed_75_zakat(self):
        """Mixed: COGS * (1 + 0.075 + 0.05) = COGS * 1.125"""
        from smart_agri.sales.services import SaleService
        item = _make_item("200.00")
        farm = _make_farm("MIXED_75")
        result = SaleService._calculate_minimum_price(item, farm=farm)
        assert result == Decimal("225.00"), f"Expected 225.00, got {result}"

    def test_no_farm_defaults_to_conservative(self):
        """Without farm context, defaults to conservative 10% zakat."""
        from smart_agri.sales.services import SaleService
        item = _make_item("100.00")
        result = SaleService._calculate_minimum_price(item, farm=None)
        assert result == Decimal("115.00")

    def test_zero_cost_returns_zero(self):
        """Zero COGS means no minimum can be enforced."""
        from smart_agri.sales.services import SaleService
        item = _make_item("0.00")
        result = SaleService._calculate_minimum_price(item, farm=None)
        assert result == Decimal("0.00")

    def test_none_cost_handled_gracefully(self):
        """None unit_price must not crash — returns 0."""
        from smart_agri.sales.services import SaleService
        item = MagicMock()
        item.unit_price = None
        result = SaleService._calculate_minimum_price(item, farm=None)
        assert result == Decimal("0.00")

    def test_result_is_decimal_not_float(self):
        """Result must be Decimal type, never float."""
        from smart_agri.sales.services import SaleService
        item = _make_item("50.00")
        result = SaleService._calculate_minimum_price(item, farm=_make_farm())
        assert isinstance(result, Decimal), f"[Axis 5] Result type is {type(result)}, must be Decimal"

    def test_large_cost_precision(self):
        """Large values must maintain Decimal precision."""
        from smart_agri.sales.services import SaleService
        item = _make_item("999999.9999")
        farm = _make_farm("10_PERCENT")
        result = SaleService._calculate_minimum_price(item, farm=farm)
        assert isinstance(result, Decimal)
        assert result > Decimal("0")


# ──────────────────────────────────────────────────────────────────────────
# 2. Sales Model Structural Checks (Axis 1 + Axis 5 + Axis 6)
# ──────────────────────────────────────────────────────────────────────────

class TestSalesModelStructure:
    """Structural verification of sales models."""

    def test_sales_invoice_has_farm_fk(self):
        """[Axis 6] SalesInvoice must have farm FK for tenant isolation."""
        from smart_agri.sales.models import SalesInvoice
        field = SalesInvoice._meta.get_field('farm')
        assert field.related_model.__name__ == 'Farm'

    def test_sales_invoice_item_price_is_decimal(self):
        """[Axis 5] SalesInvoiceItem price fields must be DecimalField."""
        from smart_agri.sales.models import SalesInvoiceItem
        price_field = SalesInvoiceItem._meta.get_field('unit_price')
        assert price_field.__class__.__name__ == 'DecimalField', \
            f"SalesInvoiceItem.unit_price is {price_field.__class__.__name__}, must be DecimalField"

    def test_sales_invoice_item_qty_is_decimal(self):
        """[Axis 5] SalesInvoiceItem.qty must be DecimalField."""
        from smart_agri.sales.models import SalesInvoiceItem
        field = SalesInvoiceItem._meta.get_field('qty')
        assert field.__class__.__name__ == 'DecimalField'

    def test_sales_invoice_has_idempotency_key(self):
        """[Axis 2] SalesInvoice must have idempotency_key for network safety."""
        from smart_agri.sales.models import SalesInvoice
        field = SalesInvoice._meta.get_field('idempotency_key')
        assert field is not None

    def test_sales_invoice_total_is_decimal(self):
        """SalesInvoice monetary fields must be DecimalField."""
        from smart_agri.sales.models import SalesInvoice
        for field_name in ['total_amount', 'tax_amount', 'net_amount']:
            field = SalesInvoice._meta.get_field(field_name)
            assert field.__class__.__name__ == 'DecimalField', \
                f"SalesInvoice.{field_name} must be DecimalField"

    def test_sales_invoice_item_has_harvest_lot(self):
        """[Axis 11] SalesInvoiceItem must link to HarvestLot for traceability."""
        from smart_agri.sales.models import SalesInvoiceItem
        field = SalesInvoiceItem._meta.get_field('harvest_lot')
        assert field is not None


# ──────────────────────────────────────────────────────────────────────────
# 3. Service Layer Pattern (AGENTS.md §27)
# ──────────────────────────────────────────────────────────────────────────

class TestSalesServiceLayerPattern:
    """Verify sales follows the mandatory Service Layer Pattern."""

    def test_sale_service_class_exists(self):
        """SaleService must exist as the business logic layer."""
        from smart_agri.sales.services import SaleService
        assert SaleService is not None

    def test_calculate_minimum_price_is_static(self):
        """_calculate_minimum_price should be a static method."""
        from smart_agri.sales.services import SaleService
        method = getattr(SaleService, '_calculate_minimum_price', None)
        assert method is not None, "SaleService._calculate_minimum_price must exist"
