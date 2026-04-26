from decimal import Decimal

from django.test import SimpleTestCase

from smart_agri.core.services.activity_labor import normalize_surrah_share


class ActivityLaborUtilsTests(SimpleTestCase):
    def test_normalize_surrah_rounds_to_quarter_day(self):
        assert normalize_surrah_share('1.13') == Decimal('1.25')

    def test_normalize_surrah_ignores_empty_or_negative_values(self):
        assert normalize_surrah_share('') == Decimal('0.00')
        assert normalize_surrah_share('-1') == Decimal('0.00')
