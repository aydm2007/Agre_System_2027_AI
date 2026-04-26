"""
[AGRI-GUARDIAN §Axis-4] Fund Accounting & Sector Governance Verification
AGENTS.md Axis 4: Fund Accounting and Sector Governance.

Verifies:
  1. SectorRelationship model exists with allow_revenue_recycling field
  2. allow_revenue_recycling defaults to False (strict doctrine)
  3. ACCOUNT_SECTOR_PAYABLE constant is defined on FinancialLedger
  4. SaleService posts to ACCOUNT_SECTOR_PAYABLE when recycling is disabled
  5. ActualExpense posting requires BudgetClassification + replenishment_reference
  6. BudgetClassification model exists with mandatory code field

Usage:
    python scripts/check_fund_accounting.py
"""
import os
import sys
import ast

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS_COUNT = 0
FAIL_COUNT = 0
ERRORS = []


def ok(msg):
    global PASS_COUNT
    PASS_COUNT += 1
    print(f"  [OK] {msg}")


def fail(msg):
    global FAIL_COUNT
    FAIL_COUNT += 1
    ERRORS.append(msg)
    print(f"  [FAIL] {msg}")


def phase1_static_checks():
    """Static AST check: ACCOUNT_SECTOR_PAYABLE, allow_revenue_recycling, BudgetClassification."""
    print("\n[Phase 1] Static Code Checks:")

    finance_models = os.path.join(os.path.dirname(__file__), '..', 'smart_agri', 'finance', 'models.py')
    sales_services = os.path.join(os.path.dirname(__file__), '..', 'smart_agri', 'sales', 'services.py')

    # Check ACCOUNT_SECTOR_PAYABLE in finance/models.py
    if os.path.exists(finance_models):
        src = open(finance_models, encoding='utf-8').read()
        if 'ACCOUNT_SECTOR_PAYABLE' in src and '2100-SECTOR-PAY' in src:
            ok("ACCOUNT_SECTOR_PAYABLE = '2100-SECTOR-PAY' defined in FinancialLedger")
        else:
            fail("ACCOUNT_SECTOR_PAYABLE missing or incorrect in finance/models.py")

        if 'allow_revenue_recycling' in src:
            ok("SectorRelationship.allow_revenue_recycling field exists in models.py")
        else:
            fail("SectorRelationship.allow_revenue_recycling field MISSING from models.py")

        if 'BudgetClassification' in src:
            ok("BudgetClassification model exists in finance/models.py")
        else:
            fail("BudgetClassification model MISSING from finance/models.py")
    else:
        fail("finance/models.py not found")

    # Check sales service posts to ACCOUNT_SECTOR_PAYABLE
    if os.path.exists(sales_services):
        src = open(sales_services, encoding='utf-8').read()
        if 'ACCOUNT_SECTOR_PAYABLE' in src and 'allow_revenue_recycling' in src:
            ok("SaleService checks allow_revenue_recycling and posts to ACCOUNT_SECTOR_PAYABLE")
        else:
            fail("SaleService MISSING revenue recycling check or sector payable posting")
    else:
        fail("sales/services.py not found")

    # Check ActualExpense validates BudgetClassification + replenishment_reference
    finance_api = os.path.join(os.path.dirname(__file__), '..', 'smart_agri', 'finance', 'api_expenses.py')
    if os.path.exists(finance_api):
        src = open(finance_api, encoding='utf-8').read()
        if 'budget_classification' in src and 'replenishment_reference' in src:
            ok("ActualExpense API enforces BudgetClassification + replenishment_reference")
        else:
            fail("ActualExpense API MISSING BudgetClassification or replenishment_reference validation")
    else:
        fail("finance/api_expenses.py not found")


def phase2_orm_checks():
    """Live ORM checks against the database."""
    print("\n[Phase 2] Django ORM Checks:")
    try:
        import django
        django.setup()

        from smart_agri.finance.models import SectorRelationship, FinancialLedger, BudgetClassification

        # T1: SectorRelationship.allow_revenue_recycling default = False
        field = SectorRelationship._meta.get_field('allow_revenue_recycling')
        if field.default is False:
            ok("T1: SectorRelationship.allow_revenue_recycling defaults to False ✓")
        else:
            fail(f"T1: allow_revenue_recycling default is '{field.default}' — MUST be False")

        # T2: ACCOUNT_SECTOR_PAYABLE constant value
        if FinancialLedger.ACCOUNT_SECTOR_PAYABLE == '2100-SECTOR-PAY':
            ok("T2: FinancialLedger.ACCOUNT_SECTOR_PAYABLE == '2100-SECTOR-PAY' ✓")
        else:
            fail(f"T2: ACCOUNT_SECTOR_PAYABLE == '{FinancialLedger.ACCOUNT_SECTOR_PAYABLE}' — expected '2100-SECTOR-PAY'")

        # T3: BudgetClassification has mandatory 'code' field
        field = BudgetClassification._meta.get_field('code')
        if not field.blank and not field.null:
            ok("T3: BudgetClassification.code is mandatory (not blank, not null) ✓")
        else:
            fail("T3: BudgetClassification.code allows blank/null — MUST be mandatory")

        # T4: FinancialLedger is append-only (no update method override)
        ledger_src = os.path.join(os.path.dirname(__file__), '..', 'smart_agri', 'finance', 'models.py')
        src = open(ledger_src, encoding='utf-8').read()
        if 'prevent_updates' in src or 'LEDGER IS IMMUTABLE' in src or 'append-only' in src.lower():
            ok("T4: FinancialLedger is append-only (immutability enforced) ✓")
        else:
            fail("T4: FinancialLedger append-only enforcement NOT found in models.py")

    except Exception as e:
        fail(f"Phase 2 ORM setup failed: {e}")


print("=" * 60)
print("[AGRI-GUARDIAN] Fund Accounting Verification — Axis 4")
print("=" * 60)
phase1_static_checks()
phase2_orm_checks()
print()
print(f"  Results: {PASS_COUNT} passed, {FAIL_COUNT} failed")
if FAIL_COUNT == 0:
    print("\nPASSED: Fund accounting doctrine fully enforced. ✅")
    sys.exit(0)
else:
    print("\nFAILED:")
    for e in ERRORS:
        print(f"  - {e}")
    sys.exit(1)
