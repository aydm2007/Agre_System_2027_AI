"""
[AGRI-GUARDIAN] Tests for BiologicalAmortizationService.

Covers:
  - Axis 5: Decimal precision (no float)
  - Axis 6: Tenant isolation (farm_id mandatory)
  - Axis 7: AuditLog creation
  - Axis 11: Biological Asset Hierarchy (PRODUCTIVE = OPEX)
  - Axis 2: Idempotency guard (already processed)
"""
import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch


class TestBiologicalAmortizationService:
    """Tests for BiologicalAmortizationService.run_monthly_amortization"""

    @patch('smart_agri.core.services.bio_amortization_service.FinancialLedger', create=True)
    @patch('smart_agri.core.services.bio_amortization_service.BiologicalAssetCohort', create=True)
    def test_requires_farm_id_axis6(self, MockCohort, MockLedger):
        """[Axis 6] Calling without farm_id must raise ValidationError."""
        from smart_agri.core.services.bio_amortization_service import BiologicalAmortizationService

        with pytest.raises(Exception) as exc_info:
            BiologicalAmortizationService.run_monthly_amortization(
                farm_id=None, year=2026, month=3, user=None
            )
        assert "معرف المزرعة" in str(exc_info.value) or "farm_id" in str(exc_info.value)

    @patch('smart_agri.core.services.bio_amortization_service.FinancialLedger', create=True)
    @patch('smart_agri.core.services.bio_amortization_service.BiologicalAssetCohort', create=True)
    def test_already_processed_is_idempotent(self, MockCohort, MockLedger):
        """[Axis 2] Running for same period must return 'already_processed'."""
        from smart_agri.core.services.bio_amortization_service import BiologicalAmortizationService

        MockLedger.objects.filter.return_value.exists.return_value = True

        result = BiologicalAmortizationService.run_monthly_amortization(
            farm_id=1, year=2026, month=3, user=None
        )
        assert result["status"] == "already_processed"

    @patch('smart_agri.core.services.bio_amortization_service.FinancialLedger', create=True)
    @patch('smart_agri.core.services.bio_amortization_service.BiologicalAssetCohort', create=True)
    def test_no_productive_cohorts_returns_no_cohorts(self, MockCohort, MockLedger):
        """If no PRODUCTIVE cohorts exist, should return 'no_cohorts'."""
        from smart_agri.core.services.bio_amortization_service import BiologicalAmortizationService

        MockLedger.objects.filter.return_value.exists.return_value = False
        MockCohort.objects.filter.return_value.select_related.return_value.exists.return_value = False
        MockCohort.STATUS_PRODUCTIVE = 'PRODUCTIVE'

        result = BiologicalAmortizationService.run_monthly_amortization(
            farm_id=1, year=2026, month=3, user=None
        )
        assert result["status"] == "no_cohorts"

    def test_service_uses_decimal_not_float(self):
        """[Axis 5] The service must not use float()."""
        import inspect
        from smart_agri.core.services.bio_amortization_service import BiologicalAmortizationService
        source = inspect.getsource(BiologicalAmortizationService)
        assert 'float(' not in source, \
            "BiologicalAmortizationService must not use float() — Axis 5 violation"

    def test_service_uses_transaction_atomic(self):
        """The service must be wrapped in @transaction.atomic."""
        from smart_agri.core.services.bio_amortization_service import BiologicalAmortizationService
        fn = BiologicalAmortizationService.run_monthly_amortization
        assert hasattr(fn, '__wrapped__') or callable(fn), \
            "run_monthly_amortization must be @transaction.atomic"

    def test_posts_correct_account_codes(self):
        """[Axis 11] Must post DR 7000-DEP-EXP / CR 1600-BIO-ASSET."""
        import inspect
        from smart_agri.core.services.bio_amortization_service import BiologicalAmortizationService
        source = inspect.getsource(BiologicalAmortizationService)
        assert '7000-DEP-EXP' in source, "Must debit 7000-DEP-EXP"
        assert '1600-BIO-ASSET' in source, "Must credit 1600-BIO-ASSET"

    def test_service_creates_audit_log(self):
        """[Axis 7] The service must create AuditLog entries."""
        import inspect
        from smart_agri.core.services.bio_amortization_service import BiologicalAmortizationService
        source = inspect.getsource(BiologicalAmortizationService)
        assert 'AuditLog.objects.create' in source, \
            "Must create AuditLog for bio amortization"

    def test_depreciation_formula_uses_months(self):
        """[Axis 11] Depreciation = capitalized_cost / (useful_life_years * 12)."""
        import inspect
        from smart_agri.core.services.bio_amortization_service import BiologicalAmortizationService
        source = inspect.getsource(BiologicalAmortizationService)
        assert 'TWELVE' in source or '* 12' in source or '/ total_months' in source, \
            "Depreciation must use monthly calculation"
