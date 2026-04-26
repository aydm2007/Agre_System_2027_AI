import inspect
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import ProgrammingError, connection
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from smart_agri.core.api.serializers.farm import FarmSerializer
from smart_agri.core.models.log import AuditLog


class FarmSerializerSalesTaxTests(SimpleTestCase):
    def test_sales_tax_percentage_returns_decimal_from_settings(self):
        class FarmStub:
            settings = type("SettingsStub", (), {"sales_tax_percentage": Decimal("15.00")})()

        value = FarmSerializer().get_sales_tax_percentage(FarmStub())
        self.assertEqual(value, Decimal("15.00"))

    def test_sales_tax_percentage_falls_back_on_schema_drift(self):
        class FarmStub:
            @property
            def settings(self):
                raise ProgrammingError("column core_farmsettings.sales_tax_percentage does not exist")

        value = FarmSerializer().get_sales_tax_percentage(FarmStub())
        self.assertEqual(value, Decimal("0.00"))


class SchemaParityRuntimeTests(TestCase):
    def test_farmsettings_sales_tax_column_exists(self):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'core_farmsettings' AND column_name = 'sales_tax_percentage'
                """
            )
            self.assertIsNotNone(cursor.fetchone())

    def test_auditlog_columns_match_runtime_contract(self):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT column_name, character_maximum_length
                FROM information_schema.columns
                WHERE table_name = 'core_auditlog'
                  AND column_name IN ('action', 'object_id')
                ORDER BY column_name
                """
            )
            rows = dict(cursor.fetchall())

        self.assertGreaterEqual(rows.get("action", 0), 100)
        self.assertGreaterEqual(rows.get("object_id", 0), 500)


class RouteBreachAuditTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="route_audit_user",
            password="123456",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_breach_endpoint_creates_audit_log(self):
        response = self.client.post(
            "/api/v1/audit/breach/",
            {"target_url": "/finance", "timestamp": "2026-03-12T00:00:00Z"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            AuditLog.objects.filter(
                actor=self.user,
                action="ROUTE_BREACH_ATTEMPT",
                model="FrontendRouter",
                object_id="/finance",
            ).exists()
        )


class IdempotencyStructureTests(SimpleTestCase):
    def test_ias41_revalue_uses_official_guard(self):
        from smart_agri.finance.api_ledger import FinancialLedgerViewSet

        source = inspect.getsource(FinancialLedgerViewSet.ias41_revalue)
        self.assertIn("_enforce_action_idempotency(", source)
        self.assertIn("@idempotent", FinancialLedgerViewSet.ias41_revalue.__doc__ or "")

    def test_timesheet_approve_uses_official_guard(self):
        from smart_agri.core.api.hr import TimesheetViewSet

        source = inspect.getsource(TimesheetViewSet.approve_entry)
        self.assertIn("_enforce_action_idempotency(", source)
        self.assertIn("@idempotent", TimesheetViewSet.approve_entry.__doc__ or "")

    def test_fuel_reconciliation_post_uses_official_guard(self):
        from smart_agri.core.views.fuel_reconciliation_dashboard import FuelReconciliationDashboardViewSet

        source = inspect.getsource(FuelReconciliationDashboardViewSet.post_reconciliation)
        self.assertIn("_enforce_action_idempotency(", source)
