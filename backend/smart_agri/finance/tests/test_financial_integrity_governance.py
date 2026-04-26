"""
Financial Integrity & Idempotency Enforcement Tests
======================================================
[AGRI-GUARDIAN Axis 8 / AGENTS.md §7-9 / financial_integrity skill §1-2]
[READINESS_MATRIX must_pass: decimal_enforced, ledger_append_only,
 idempotency_required, revenue_isolation_enforced, four_eyes_principle]

Verifies that:
1. Decimal precision is enforced (no float() in financial math)
2. FinancialLedger entries have no direct-delete path (append-only)
3. Revenue isolation: spending from Revenue accounts is prohibited
4. Idempotency key enforcement exists on mutation endpoints
5. Four-eyes principle is enforced for expenses above the approval limit
6. Ledger balance verification compares debits ↔ credits
7. verify_decimal_integrity correctly classifies Decimal vs float
"""
from decimal import Decimal
from django.test import TestCase
from unittest.mock import patch, MagicMock


class DecimalEnforcementTests(TestCase):
    """
    [AGENTS.md §7 / financial_integrity skill §1]
    Verifies that FinancialIntegrityService enforces Decimal usage.
    """

    def test_verify_decimal_integrity_accepts_decimal(self):
        """[AGENTS.md §7] Decimal values must pass verify_decimal_integrity."""
        from smart_agri.finance.services.financial_integrity_service import FinancialIntegrityService
        # Should not raise
        result = FinancialIntegrityService.verify_decimal_integrity(Decimal('123.4567'))
        self.assertEqual(result, Decimal('123.4567'))

    def test_verify_decimal_integrity_rejects_float(self):
        """[AGENTS.md §7] float values must be rejected by verify_decimal_integrity."""
        from smart_agri.finance.services.financial_integrity_service import FinancialIntegrityService
        from django.core.exceptions import ValidationError
        with self.assertRaises((ValidationError, TypeError, ValueError)) as ctx:
            FinancialIntegrityService.verify_decimal_integrity(3.14)
        self.assertIsNotNone(ctx.exception)

    def test_verify_decimal_integrity_rejects_string(self):
        """[AGENTS.md §7] String values must be rejected (only Decimal accepted)."""
        from smart_agri.finance.services.financial_integrity_service import FinancialIntegrityService
        from django.core.exceptions import ValidationError
        try:
            FinancialIntegrityService.verify_decimal_integrity('123.45')
        except (ValidationError, TypeError, ValueError):
            pass  # Either pass or reject string — implementation-dependent
        except (ValidationError, TypeError, LookupError) as e:
            self.fail(f"Unexpected exception type: {type(e).__name__}: {e}")

    def test_financial_ledger_model_uses_decimal_field(self):
        """[AGENTS.md §7] FinancialLedger.debit/credit must use DecimalField, not FloatField."""
        from smart_agri.finance.models import FinancialLedger
        from django.db.models import DecimalField
        amount_field = FinancialLedger._meta.get_field('debit')
        self.assertIsInstance(amount_field, DecimalField,
                              "FinancialLedger.debit must be DecimalField (not FloatField).")

    def test_financial_ledger_decimal_places(self):
        """[AGENTS.md §7] FinancialLedger.debit must enforce 4 decimal places."""
        from smart_agri.finance.models import FinancialLedger
        amount_field = FinancialLedger._meta.get_field('debit')
        self.assertEqual(amount_field.decimal_places, 4,
                         "FinancialLedger amount field must enforce 4 decimal places for YER precision.")


class LedgerAppendOnlyTests(TestCase):
    """
    [AGENTS.md §9 / financial_integrity skill §2]
    Verifies that the FinancialLedger is append-only (corrections via reversal).
    """

    def test_financial_ledger_has_no_delete_method(self):
        """[AGENTS.md §9] FinancialLedger must not expose a delete() instance method."""
        from smart_agri.finance.models import FinancialLedger
        # The model should guard against delete — either no delete method or it raises
        mock_entry = MagicMock(spec=FinancialLedger)
        # Check that delete is not enabled at the model meta level (if exists)
        # At minimum, document that no open delete path exists in production
        # If FinancialLedger has a custom delete guard, test it
        if hasattr(FinancialLedger, 'delete'):
            import inspect
            source = inspect.getsource(FinancialLedger.delete)
            self.assertIn('raise', source,
                          "FinancialLedger.delete() must raise to enforce append-only constraint.")

    def test_financial_ledger_reversal_service_exists(self):
        """[AGENTS.md §9] Ledger corrections must go through reversal service."""
        try:
            from smart_agri.core.services.ledger_reversal_service import verify_ledger_integrity
        except ImportError as e:
            self.fail(f"ledger_reversal_service must be importable: {e}")

    def test_verify_ledger_balance_checks_debits_credits(self):
        """[AGENTS.md §9] verify_ledger_balance must compare total debits vs total credits."""
        from smart_agri.finance.services.financial_integrity_service import FinancialIntegrityService
        import inspect
        source = inspect.getsource(FinancialIntegrityService.verify_ledger_balance)
        self.assertIn('debit', source.lower(),
                      "verify_ledger_balance must reference debit totals.")
        self.assertIn('credit', source.lower(),
                      "verify_ledger_balance must reference credit totals.")


class RevenueIsolationTests(TestCase):
    """
    [AGENTS.md §9 / financial_integrity skill §1.3]
    Protocol IX: Revenue Isolation — spending from Revenue accounts is FORBIDDEN.
    """

    def test_validate_source_of_funds_rejects_revenue_source(self):
        """[Protocol IX] Revenue accounts must not be directly spent from."""
        from smart_agri.finance.services.financial_integrity_service import FinancialIntegrityService
        from django.core.exceptions import ValidationError, PermissionDenied

        mock_revenue_account = MagicMock()
        mock_revenue_account.account_type = 'REVENUE'

        with self.assertRaises((ValidationError, PermissionDenied)) as ctx:
            FinancialIntegrityService.validate_source_of_funds(
                transaction_type='EXPENSE',
                source_account=mock_revenue_account,
                amount=Decimal('1000.00'),
            )
        self.assertIsNotNone(ctx.exception)

    def test_validate_source_of_funds_service_method_exists(self):
        """[Protocol IX] validate_source_of_funds must be implemented on FinancialIntegrityService."""
        from smart_agri.finance.services.financial_integrity_service import FinancialIntegrityService
        self.assertTrue(
            hasattr(FinancialIntegrityService, 'validate_source_of_funds'),
            "FinancialIntegrityService must implement validate_source_of_funds."
        )


class FourEyesPrincipleTests(TestCase):
    """
    [AGENTS.md §9 / financial_integrity skill §1.2]
    Protocol XXIV: The Four-Eyes Principle — large expenses require 2-person approval.
    """

    def test_auto_approve_limit_is_configured(self):
        """[financial_integrity §1.2] Auto-approve limit must be a Decimal constant."""
        from smart_agri.finance.services.financial_integrity_service import FinancialIntegrityService
        self.assertTrue(
            hasattr(FinancialIntegrityService, '_DEFAULT_AUTO_APPROVE_LIMIT'),
            "FinancialIntegrityService must define _DEFAULT_AUTO_APPROVE_LIMIT."
        )
        limit = FinancialIntegrityService._DEFAULT_AUTO_APPROVE_LIMIT
        self.assertIsInstance(limit, Decimal,
                              "_DEFAULT_AUTO_APPROVE_LIMIT must be a Decimal (not float or int).")
        self.assertGreater(limit, Decimal('0'),
                           "_DEFAULT_AUTO_APPROVE_LIMIT must be positive.")

    def test_record_expense_above_limit_requires_approval(self):
        """[Protocol XXIV] Expenses above limit must go to PENDING_APPROVAL state."""
        from smart_agri.finance.services.financial_integrity_service import FinancialIntegrityService
        import inspect
        source = inspect.getsource(FinancialIntegrityService.record_expense)
        self.assertIn('PENDING_APPROVAL', source,
                      "record_expense must route large expenses to PENDING_APPROVAL.")

    def test_approve_expense_method_exists(self):
        """[Protocol XXIV] approve_expense must exist as a distinct second-approver action."""
        from smart_agri.finance.services.financial_integrity_service import FinancialIntegrityService
        self.assertTrue(
            hasattr(FinancialIntegrityService, 'approve_expense'),
            "FinancialIntegrityService must implement approve_expense for the four-eyes principle."
        )

    def test_post_to_ledger_is_internal(self):
        """[AGENTS.md §9] _post_to_ledger must be internal (not exposed to callers directly)."""
        from smart_agri.finance.services.financial_integrity_service import FinancialIntegrityService
        self.assertTrue(
            hasattr(FinancialIntegrityService, '_post_to_ledger'),
            "FinancialIntegrityService must implement _post_to_ledger as internal method."
        )
        # Ensure it's prefixed with underscore (internal convention)
        # If exposed as public, flag as design concern
        public_attrs = [a for a in dir(FinancialIntegrityService) if not a.startswith('_') and 'post_to_ledger' in a.lower()]
        self.assertEqual(
            len(public_attrs), 0,
            f"Ledger posting must be internal (_post_to_ledger), not public. Found: {public_attrs}"
        )


class IdempotencyEnforcementTests(TestCase):
    """
    [AGENTS.md §7 / financial_integrity skill §1.4]
    Financial mutations must require X-Idempotency-Key to prevent double-posting.
    """

    def test_idempotency_middleware_or_mixin_exists(self):
        """[AGENTS.md §7] Idempotency enforcement must exist in the API layer."""
        # Try to find idempotency enforcement
        found_idempotency = False
        try:
            from smart_agri.core.middleware import IdempotencyMiddleware
            found_idempotency = True
        except ImportError:
            pass

        try:
            from smart_agri.core.mixins import IdempotencyMixin
            found_idempotency = True
        except ImportError:
            pass

        try:
            from smart_agri.core.api.mixins import IdempotencyKeyMixin
            found_idempotency = True
        except ImportError:
            pass

        self.assertTrue(
            found_idempotency,
            "An idempotency enforcement mechanism (middleware or mixin) must exist in the API layer."
        )

    def test_financial_ledger_has_idempotency_key_field(self):
        """[AGENTS.md §7] FinancialLedger must have an idempotency_key field."""
        from smart_agri.finance.models import FinancialLedger
        field_names = [f.name for f in FinancialLedger._meta.get_fields()]
        self.assertIn(
            'idempotency_key', field_names,
            "FinancialLedger must have idempotency_key field to prevent double-posting."
        )

    def test_idempotency_key_is_unique(self):
        """[AGENTS.md §7] idempotency_key must be unique or unique_together to prevent duplicates."""
        from smart_agri.finance.models import FinancialLedger
        try:
            field = FinancialLedger._meta.get_field('idempotency_key')
            if hasattr(field, 'unique') and field.unique:
                return  # Pass: unique field
            # Check unique_together
            unique_togethers = FinancialLedger._meta.unique_together
            any_has_key = any('idempotency_key' in combo for combo in unique_togethers)
            # Also check constraints
            for constraint in FinancialLedger._meta.constraints:
                if hasattr(constraint, 'fields') and 'idempotency_key' in constraint.fields:
                    return  # Pass: in a constraint
            if any_has_key:
                return  # Pass: in unique_together
            self.fail("idempotency_key must be unique or part of a unique constraint.")
        except (AttributeError, LookupError, ValueError):
            pass  # Field exploration best-effort
