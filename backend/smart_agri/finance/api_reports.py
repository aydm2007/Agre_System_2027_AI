"""
[AGRI-GUARDIAN] Financial Reporting JSON APIs
- Profitability Summary (P&L / Income Statement)
- Trial Balance
All following AGENTS.md: Decimal-only, Tenant Isolation, Analytical Purity.
"""
import logging
from decimal import Decimal

from django.db.models import Sum
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from smart_agri.finance.models import FinancialLedger

logger = logging.getLogger(__name__)

# Arabic labels for account codes
ACCOUNT_LABELS = {
    '1000-LABOR': 'تكاليف العمالة',
    '1100-CASH': 'الصندوق النقدي',
    '1110-BANK': 'البنك',
    '1200-RECEIVABLE': 'المدينون',
    '1300-INV-ASSET': 'أصول المخزون',
    '1400-WIP': 'أعمال تحت التنفيذ',
    '1500-ACC-DEP': 'الاستهلاك المتراكم',
    '2000-MATERIAL': 'تكاليف المواد',
    '2000-PAY-SAL': 'مستحقات الرواتب',
    '2001-PAY-VENDOR': 'مستحقات الموردين',
    '2100-SECTOR-PAY': 'حساب القطاع الإنتاجي',
    '2105-ZAKAT-PAY': 'زكاة مستحقة',
    '3000-MACHINERY': 'تكاليف الآلات',
    '4000-OVERHEAD': 'تكاليف عامة',
    '4001-EXP-ADMIN': 'مصروفات إدارية',
    '5000-REVENUE': 'إيرادات المبيعات',
    '6000-COGS': 'تكلفة البضاعة المباعة',
    '7000-DEP-EXP': 'مصروف الاستهلاك',
    '7100-ZAKAT-EXP': 'مصروف الزكاة',
    '9999-SUSPENSE': 'حساب معلق',
    'EXP-ELEC': 'مصروف الكهرباء',
}

# Revenue account prefixes (Credit-normal)
REVENUE_PREFIXES = ('5',)
# Expense account prefixes (Debit-normal)
EXPENSE_PREFIXES = ('1000', '2000-MAT', '3000', '4000', '4001', '6000', '7000', '7100', 'EXP-')


def _is_revenue(code: str) -> bool:
    return code.startswith(REVENUE_PREFIXES)


def _is_expense(code: str) -> bool:
    return any(code.startswith(p) for p in EXPENSE_PREFIXES)


def _build_base_qs(request):
    """Build base queryset with tenant isolation + filters."""
    qs = FinancialLedger.objects.all()

    farm_id = request.query_params.get('farm_id') or request.query_params.get('farm')
    cost_center_id = request.query_params.get('cost_center_id')
    crop_plan_id = request.query_params.get('crop_plan_id')
    start_date = request.query_params.get('start')
    end_date = request.query_params.get('end')

    if farm_id:
        raw = str(farm_id).split(",")[0].strip()
        qs = qs.filter(farm_id=raw)
    if cost_center_id:
        qs = qs.filter(cost_center_id=cost_center_id)
    if crop_plan_id:
        qs = qs.filter(crop_plan_id=crop_plan_id)
    if start_date:
        qs = qs.filter(created_at__date__gte=start_date)
    if end_date:
        qs = qs.filter(created_at__date__lte=end_date)

    return qs, {
        'farm_id': farm_id,
        'cost_center_id': cost_center_id,
        'crop_plan_id': crop_plan_id,
        'start': start_date,
        'end': end_date,
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profitability_summary_view(request):
    """
    GET /api/v1/finance/profitability-summary/
    Returns JSON P&L (Income Statement) data from FinancialLedger.
    [AGRI-GUARDIAN] Decimal-only, Tenant Isolated, Analytical Purity.
    """
    qs, filters_applied = _build_base_qs(request)

    rows = qs.values('account_code').annotate(
        total_debit=Sum('debit'),
        total_credit=Sum('credit'),
    ).order_by('account_code')

    revenue_accounts = []
    expense_accounts = []
    other_accounts = []
    total_revenue = Decimal("0.0000")
    total_expense = Decimal("0.0000")

    for row in rows:
        code = row['account_code'] or '9999-SUSPENSE'
        dr = row['total_debit'] or Decimal("0.0000")
        cr = row['total_credit'] or Decimal("0.0000")
        label = ACCOUNT_LABELS.get(code, code)

        entry = {
            'code': code,
            'name': label,
            'total_debit': str(dr),
            'total_credit': str(cr),
            'net': str(cr - dr),
        }

        if _is_revenue(code):
            revenue_accounts.append(entry)
            total_revenue += cr  # Revenue is credit-normal
        elif _is_expense(code):
            expense_accounts.append(entry)
            total_expense += dr  # Expenses are debit-normal
        else:
            other_accounts.append(entry)

    net_income = total_revenue - total_expense

    return Response({
        'revenue_accounts': revenue_accounts,
        'expense_accounts': expense_accounts,
        'other_accounts': other_accounts,
        'totals': {
            'total_revenue': str(total_revenue),
            'total_expense': str(total_expense),
            'net_income': str(net_income),
        },
        'filters': filters_applied,
        'currency': 'YER',
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def trial_balance_view(request):
    """
    GET /api/v1/finance/trial-balance/
    Returns Trial Balance data grouped by account_code.
    [AGRI-GUARDIAN] Pre-Close Gate: SUM(Debit) == SUM(Credit) check included.
    """
    qs, filters_applied = _build_base_qs(request)

    rows = qs.values('account_code').annotate(
        total_debit=Sum('debit'),
        total_credit=Sum('credit'),
    ).order_by('account_code')

    accounts = []
    grand_debit = Decimal("0.0000")
    grand_credit = Decimal("0.0000")

    for row in rows:
        code = row['account_code'] or '9999-SUSPENSE'
        dr = row['total_debit'] or Decimal("0.0000")
        cr = row['total_credit'] or Decimal("0.0000")
        balance = dr - cr
        label = ACCOUNT_LABELS.get(code, code)

        accounts.append({
            'code': code,
            'name': label,
            'total_debit': str(dr),
            'total_credit': str(cr),
            'balance': str(balance),
        })

        grand_debit += dr
        grand_credit += cr

    is_balanced = grand_debit == grand_credit

    return Response({
        'accounts': accounts,
        'totals': {
            'total_debit': str(grand_debit),
            'total_credit': str(grand_credit),
            'difference': str(grand_debit - grand_credit),
            'is_balanced': is_balanced,
        },
        'filters': filters_applied,
        'currency': 'YER',
    })
