from __future__ import annotations

from decimal import Decimal

from smart_agri.core.services.decimal_guard import coerce_decimal
from smart_agri.core.services.harvest_service import HarvestService


class SovereignZakatService:
    """Enterprise wrapper for sovereign/zakat postings, disclosure, and readiness."""

    @staticmethod
    def calculate(*, quantity, zakat_rule: str, unit_cost=0, sovereign_rate=0) -> dict:
        qty = coerce_decimal(quantity)
        zakat_qty = HarvestService.calculate_zakat_due(qty, zakat_rule)
        cost = coerce_decimal(unit_cost)
        sovereign_rate_dec = coerce_decimal(sovereign_rate, places=Decimal("0.000001"))
        sovereign_qty = (qty * sovereign_rate_dec).quantize(Decimal("0.0001"))
        return {
            "gross_qty": str(qty),
            "zakat_qty": str(zakat_qty),
            "sovereign_qty": str(sovereign_qty),
            "zakat_value": str((zakat_qty * cost).quantize(Decimal("0.0001"))),
            "sovereign_value": str((sovereign_qty * cost).quantize(Decimal("0.0001"))),
            "zakat_rule": zakat_rule,
            "disclosure_ready": qty > 0,
        }
