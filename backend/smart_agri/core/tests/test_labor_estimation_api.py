from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models import Farm, LaborRate
from smart_agri.core.models.hr import Employee, EmploymentCategory


class LaborEstimationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user("labor-estimator", password="pass123")
        self.client.force_authenticate(self.user)

        self.farm = Farm.objects.create(name="Farm One", slug="farm-one", region="North")
        self.other_farm = Farm.objects.create(name="Farm Two", slug="farm-two", region="South")
        FarmMembership.objects.create(user=self.user, farm=self.farm, role="Manager")

        LaborRate.objects.create(
            farm=self.farm,
            role_name="عامل يومي",
            daily_rate=Decimal("1800.0000"),
            cost_per_hour=Decimal("225.0000"),
            effective_date=date.today(),
        )

        self.emp1 = Employee.objects.create(
            farm=self.farm,
            first_name="Ali",
            last_name="One",
            employee_id="EMP-LAB-1",
            category=EmploymentCategory.CASUAL,
            payment_mode="SURRA",
            shift_rate=Decimal("2200.0000"),
        )
        self.emp2 = Employee.objects.create(
            farm=self.farm,
            first_name="Sami",
            last_name="Two",
            employee_id="EMP-LAB-2",
            category=EmploymentCategory.CASUAL,
            payment_mode="SURRA",
            shift_rate=Decimal("2000.0000"),
        )
        self.foreign_emp = Employee.objects.create(
            farm=self.other_farm,
            first_name="Naji",
            last_name="Three",
            employee_id="EMP-LAB-3",
            category=EmploymentCategory.CASUAL,
            payment_mode="SURRA",
            shift_rate=Decimal("2100.0000"),
        )

    def test_labor_estimate_preview_casual_success(self):
        payload = {
            "farm_id": self.farm.id,
            "labor_entry_mode": "CASUAL_BATCH",
            "surrah_count": "1.5000",
            "workers_count": 10,
            "period_hours": "8.0000",
        }
        response = self.client.post("/api/v1/labor-estimates/preview/", payload, format="json")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["equivalent_hours_per_worker"], "12.0000")
        self.assertEqual(data["equivalent_hours_total"], "120.0000")
        self.assertEqual(data["estimated_labor_cost"], "27000.0000")
        self.assertEqual(data["rate_basis"], "farm_labor_rate")

    def test_labor_estimate_preview_registered_success(self):
        payload = {
            "farm_id": self.farm.id,
            "labor_entry_mode": "REGISTERED",
            "surrah_count": "1.2500",
            "employee_ids": [self.emp1.id, self.emp2.id],
        }
        response = self.client.post("/api/v1/labor-estimates/preview/", payload, format="json")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["equivalent_hours_per_worker"], "10.0000")
        self.assertEqual(data["equivalent_hours_total"], "20.0000")
        self.assertEqual(data["estimated_labor_cost"], "5250.0000")
        self.assertEqual(data["rate_basis"], "employee_shift_rates")

    def test_labor_estimate_farm_scope_forbidden(self):
        payload = {
            "farm_id": self.other_farm.id,
            "labor_entry_mode": "CASUAL_BATCH",
            "surrah_count": "1.0000",
            "workers_count": 5,
        }
        response = self.client.post("/api/v1/labor-estimates/preview/", payload, format="json")
        self.assertEqual(response.status_code, 403)

    def test_labor_estimate_invalid_payload_400(self):
        payload = {
            "farm_id": self.farm.id,
            "labor_entry_mode": "CASUAL_BATCH",
            "surrah_count": "1.0000",
        }
        response = self.client.post("/api/v1/labor-estimates/preview/", payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("workers_count", response.json())

    def test_labor_estimate_decimal_precision(self):
        payload = {
            "farm_id": self.farm.id,
            "labor_entry_mode": "REGISTERED",
            "surrah_count": "0.3333",
            "period_hours": "8.0000",
            "employee_ids": [self.emp1.id],
        }
        response = self.client.post("/api/v1/labor-estimates/preview/", payload, format="json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["equivalent_hours_per_worker"], "2.6664")
        self.assertRegex(data["estimated_labor_cost"], r"^\d+\.\d{4}$")

    def test_labor_estimate_registered_cross_farm_employees_blocked(self):
        payload = {
            "farm_id": self.farm.id,
            "labor_entry_mode": "REGISTERED",
            "surrah_count": "1.0000",
            "employee_ids": [self.emp1.id, self.foreign_emp.id],
        }
        response = self.client.post("/api/v1/labor-estimates/preview/", payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("employee_ids", response.json())
