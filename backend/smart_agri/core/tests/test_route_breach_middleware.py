from django.contrib.auth.models import Permission, User
import json
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.middleware.route_breach_middleware import RouteBreachAuditMiddleware
from smart_agri.core.models.farm import Farm
from smart_agri.core.models.log import AuditLog
from smart_agri.core.models.settings import FarmSettings


class RouteBreachAuditMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="finance_user", password="pass")
        self.user.user_permissions.add(Permission.objects.get(codename="view_financialledger"))
        self.farm = Farm.objects.create(name="Simple Farm", slug="simple-farm", region="A")
        FarmSettings.objects.create(farm=self.farm, mode=FarmSettings.MODE_SIMPLE)
        FarmMembership.objects.create(user=self.user, farm=self.farm, role="Ø§Ù„Ù…Ø¯ÙŠØ± Ø§Ù„Ù…Ø§Ù„ÙŠ Ù„Ù„Ù…Ø²Ø±Ø¹Ø©")

    def test_finance_route_breach_is_blocked_and_audited_in_simple_mode(self):
        middleware = RouteBreachAuditMiddleware(lambda request: HttpResponse("ok"))
        request = self.factory.get(
            "/api/v1/finance/treasury-transactions/",
            HTTP_X_FARM_ID=str(self.farm.id),
        )
        request.user = self.user

        response = middleware(request)

        self.assertEqual(response.status_code, 403)
        body = json.loads(response.content.decode("utf-8"))
        self.assertEqual(body["code"], "ROUTE_BREACH_SIMPLE_MODE")
        audit = AuditLog.objects.get(action="ROUTE_BREACH_ATTEMPT")
        self.assertEqual(audit.actor, self.user)
        self.assertEqual(audit.new_payload["farm_id"], self.farm.id)
        self.assertEqual(audit.new_payload["path"], "/api/v1/finance/treasury-transactions/")
        self.assertEqual(audit.new_payload["breach_surface"], "finance")

    def test_governed_contract_mutation_is_blocked_and_audited_in_simple_mode(self):
        middleware = RouteBreachAuditMiddleware(lambda request: HttpResponse("ok"))
        request = self.factory.post(
            "/api/v1/sharecropping-contracts/99/record-rent-payment/",
            data="{}",
            content_type="application/json",
            HTTP_X_FARM_ID=str(self.farm.id),
        )
        request.user = self.user

        response = middleware(request)

        self.assertEqual(response.status_code, 403)
        body = json.loads(response.content.decode("utf-8"))
        self.assertEqual(body["code"], "ROUTE_BREACH_SIMPLE_MODE")
        audit = AuditLog.objects.filter(action="ROUTE_BREACH_ATTEMPT").order_by("-id").first()
        self.assertEqual(audit.new_payload["breach_surface"], "governed_mutation")
        self.assertEqual(
            audit.new_payload["path"],
            "/api/v1/sharecropping-contracts/99/record-rent-payment/",
        )

    def test_admin_breach_also_creates_audit_log(self):
        self.user.is_superuser = True
        self.user.save()
        
        middleware = RouteBreachAuditMiddleware(lambda request: HttpResponse("ok"))
        request = self.factory.get(
            "/api/v1/finance/treasury-transactions/",
            HTTP_X_FARM_ID=str(self.farm.id),
        )
        request.user = self.user

        response = middleware(request)

        # Even admin is blocked from routine route execution outside of emergency modes
        # And must generate an audit log
        self.assertEqual(response.status_code, 403)
        audit = AuditLog.objects.filter(action="ROUTE_BREACH_ATTEMPT", actor=self.user).first()
        self.assertIsNotNone(audit)

