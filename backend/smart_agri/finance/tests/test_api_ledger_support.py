from decimal import Decimal

from django.test import SimpleTestCase

from smart_agri.finance.api_ledger_support import compute_material_variance_report, summarize_ledger_queryset


class FakeValuesResult:
    def __init__(self, rows):
        self.rows = rows

    def annotate(self, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self.rows


class FakeLedgerQuerySet:
    def __init__(self, totals, rows):
        self._totals = totals
        self._rows = rows

    def aggregate(self, **kwargs):
        return self._totals

    def values(self, *args, **kwargs):
        return FakeValuesResult(self._rows)


class LedgerSupportTests(SimpleTestCase):
    def test_summarize_ledger_queryset_computes_balance_and_count(self):
        qs = FakeLedgerQuerySet(
            totals={
                'total_debit': Decimal('12.5000'),
                'total_credit': Decimal('2.2500'),
                'entry_count': 3,
            },
            rows=[{'account_code': '1000', 'debit': Decimal('12.5000'), 'credit': Decimal('2.2500')}],
        )

        payload = summarize_ledger_queryset(qs)

        self.assertEqual(payload['totals']['balance'], Decimal('10.2500'))
        self.assertEqual(payload['totals']['entry_count'], 3)
        self.assertEqual(payload['by_account'][0]['account_code'], '1000')

    def test_compute_material_variance_report_handles_zero_actual_quantity(self):
        payload = compute_material_variance_report({
            1: {
                'item_name': 'Fertilizer',
                'std_qty': Decimal('10'),
                'std_cost_per_unit': Decimal('2.5'),
                'actual_qty': Decimal('0'),
                'actual_cost': Decimal('0'),
            }
        })

        self.assertEqual(payload['overall_summary']['total_quantity_variance'], '25.0000')
        self.assertEqual(payload['overall_summary']['total_price_variance'], '0.0000')
        self.assertEqual(payload['detailed_materials'][0]['actual_cost_per_unit'], '0')
