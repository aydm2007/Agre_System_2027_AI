from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models.farm import Farm
from smart_agri.core.models.log import AuditLog
from smart_agri.core.models.settings import FarmSettings


User = get_user_model()


class StrictRouteLeakageIntegrationTests(APITestCase):
    """
    [Phase 3: Strict Boundary Sealing]
    Integration tests for SIMPLE vs STRICT route leakage behavior.
    """

    def setUp(self):
        self.user = User.objects.create_user(username="simple_tester", password="pass")
        self.farm = Farm.objects.create(name="Simple Integration Farm", slug="simple-int-farm")
        FarmSettings.objects.create(farm=self.farm, mode=FarmSettings.MODE_SIMPLE)
        FarmMembership.objects.create(user=self.user, farm=self.farm, role="مدير القطاع")
        # Middleware runs before DRF force_authenticate, so use session auth here.
        self.client.force_login(self.user)

    def test_finance_route_leakage_blocked(self):
        """
        SIMPLE users receive 403 plus AuditLog evidence on governed finance surfaces.
        """
        response = self.client.get(
            "/api/v1/finance/ledger/",
            HTTP_X_FARM_ID=str(self.farm.id),
        )

        self.assertEqual(response.status_code, 403, "Finance route must return 403 in SIMPLE mode")

        data = response.json()
        self.assertEqual(data.get("code"), "ROUTE_BREACH_SIMPLE_MODE")
        self.assertIn("غير مصرح", data.get("detail", ""))

        audit_exists = AuditLog.objects.filter(
            action="ROUTE_BREACH_ATTEMPT",
            actor=self.user,
            new_payload__path="/api/v1/finance/ledger/",
        ).exists()
        self.assertTrue(audit_exists, "AuditLog must be emitted for SIMPLE mode route breach")

    def test_governed_mutation_route_leakage_blocked(self):
        """
        Governed mutations remain blocked in SIMPLE mode even when the route exists.
        """
        response = self.client.post(
            "/api/v1/sharecropping-contracts/",
            data={},
            format="json",
            HTTP_X_FARM_ID=str(self.farm.id),
        )
        self.assertEqual(response.status_code, 403, "Governed mutation must return 403 in SIMPLE mode")

        data = response.json()
        self.assertEqual(data.get("code"), "ROUTE_BREACH_SIMPLE_MODE")

        audit_exists = AuditLog.objects.filter(
            action="ROUTE_BREACH_ATTEMPT",
            actor=self.user,
            new_payload__path="/api/v1/sharecropping-contracts/",
        ).exists()
        self.assertTrue(audit_exists, "AuditLog must be emitted for SIMPLE mode governed mutation")

    def test_strict_farm_can_access_finance_routes(self):
        """
        STRICT mode farms can access governed finance routes.
        """
        strict_farm = Farm.objects.create(name="Strict Integration Farm", slug="strict-int-farm")
        FarmSettings.objects.create(farm=strict_farm, mode=FarmSettings.MODE_STRICT)
        FarmMembership.objects.create(user=self.user, farm=strict_farm, role="مدير النظام")

        response = self.client.get(
            "/api/v1/finance/ledger/",
            HTTP_X_FARM_ID=str(strict_farm.id),
        )

        self.assertNotEqual(
            response.status_code,
            403,
            "STRICT mode must not be blocked by SIMPLE route-breach middleware.",
        )
        breach_logged = AuditLog.objects.filter(
            action="ROUTE_BREACH_ATTEMPT",
            actor=self.user,
            new_payload__path="/api/v1/finance/ledger/",
        ).exists()
        self.assertFalse(breach_logged, "STRICT mode access must not emit SIMPLE route-breach audit evidence")

    def test_strict_routes_not_registered_in_simple(self):
        """
        [M3.4] SIMPLE navigation must not list governed finance routes.
        """
        from smart_agri.core.services.mode_policy_service import allowed_finance_routes

        routes = allowed_finance_routes(farm=self.farm)
        self.assertNotIn("/api/v1/finance/ledger/", routes)
        self.assertNotIn("/api/v1/finance/treasury-transactions/", routes)

    def test_admin_cannot_bypass_route_registration(self):
        """
        [M3.4] Superuser status does not bypass farm mode boundaries by default.
        """
        self.user.is_superuser = True
        self.user.save(update_fields=["is_superuser"])
        self.client.force_login(self.user)

        response = self.client.get(
            "/api/v1/finance/ledger/",
            HTTP_X_FARM_ID=str(self.farm.id),
        )

        self.assertEqual(response.status_code, 403, "Admin must be bound to farm mode for route access")
