from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP, getcontext

FOUR_DP = Decimal("0.0001")
TWO_DP = Decimal("0.01")
HUNDRED = Decimal("100")


def coerce_decimal(value, *, places: Decimal = FOUR_DP) -> Decimal:
    return Decimal(str(value or 0)).quantize(places, rounding=ROUND_HALF_UP)


def safe_decimal_divide(numerator, denominator, *, places: Decimal = FOUR_DP) -> Decimal:
    num = Decimal(str(numerator or 0))
    den = Decimal(str(denominator or 0))
    if den == 0:
        return Decimal("0").quantize(places, rounding=ROUND_HALF_UP)
    return getcontext().divide(num, den).quantize(places, rounding=ROUND_HALF_UP)


def safe_percentage(numerator, denominator, *, places: Decimal = TWO_DP) -> Decimal:
    ratio = safe_decimal_divide(numerator, denominator, places=Decimal("0.00000001"))
    return (ratio * HUNDRED).quantize(places, rounding=ROUND_HALF_UP)
