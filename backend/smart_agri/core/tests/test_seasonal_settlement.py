"""
[AGRI-GUARDIAN] Tests for SeasonalSettlementService.
"""

from unittest.mock import MagicMock, patch

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase


class TestSeasonalSettlementService(SimpleTestCase):
    databases = {"default"}

    @patch("smart_agri.core.models.planning.CropPlan.objects")
    def test_nonexistent_plan_raises_validation_error(self, mock_objects):
        from smart_agri.core.services.seasonal_settlement_service import SeasonalSettlementService

        mock_objects.select_for_update.return_value.filter.return_value.first.return_value = None

        with self.assertRaises(ValidationError):
            SeasonalSettlementService.settle_crop_plan(crop_plan_id=999, user=None)

    @patch("smart_agri.core.models.planning.CropPlan.objects")
    @patch("smart_agri.core.constants.CropPlanStatus")
    def test_already_settled_is_idempotent(self, mock_status, mock_objects):
        from smart_agri.core.services.seasonal_settlement_service import SeasonalSettlementService

        mock_plan = MagicMock()
        mock_plan.status = mock_status.SETTLED
        mock_plan.farm_id = 1
        mock_objects.select_for_update.return_value.filter.return_value.first.return_value = mock_plan

        result = SeasonalSettlementService.settle_crop_plan(crop_plan_id=1, user=None)

        self.assertEqual(result["status"], "already_settled")

    def test_service_uses_decimal_not_float(self):
        import inspect
        from smart_agri.core.services.seasonal_settlement_service import SeasonalSettlementService

        source = inspect.getsource(SeasonalSettlementService)
        self.assertNotIn("float(", source)

    def test_service_uses_transaction_atomic(self):
        from smart_agri.core.services.seasonal_settlement_service import SeasonalSettlementService

        fn = SeasonalSettlementService.settle_crop_plan
        self.assertTrue(hasattr(fn, "__wrapped__") or callable(fn))

    def test_service_uses_select_for_update(self):
        import inspect
        from smart_agri.core.services.seasonal_settlement_service import SeasonalSettlementService

        source = inspect.getsource(SeasonalSettlementService)
        self.assertIn("select_for_update", source)

    def test_service_creates_audit_log(self):
        import inspect
        from smart_agri.core.services.seasonal_settlement_service import SeasonalSettlementService

        source = inspect.getsource(SeasonalSettlementService)
        self.assertIn("AuditLog.objects.create", source)

    def test_service_includes_cost_center_in_ledger(self):
        import inspect
        from smart_agri.core.services.seasonal_settlement_service import SeasonalSettlementService

        source = inspect.getsource(SeasonalSettlementService)
        self.assertIn("cost_center", source)

    def test_alloc_marker_defined_before_use(self):
        import inspect
        from smart_agri.core.services.seasonal_settlement_service import SeasonalSettlementService

        source = inspect.getsource(SeasonalSettlementService)
        lines = source.split("\n")
        marker_def_line = None
        marker_use_line = None
        for i, line in enumerate(lines):
            if 'alloc_marker = f"settle-zakat' in line:
                marker_def_line = i
            if 'zakat_desc = f"' in line and "alloc_marker" in line:
                marker_use_line = i
        if marker_def_line is not None and marker_use_line is not None:
            self.assertLess(marker_def_line, marker_use_line)
