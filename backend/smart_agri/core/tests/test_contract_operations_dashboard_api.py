from decimal import Decimal
from datetime import timedelta
from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models import AuditLog, Crop, Farm, Season
from smart_agri.core.models.partnerships import (
    IrrigationType,
    SharecroppingContract,
    SharecroppingReceipt,
    TouringAssessment,
)
from smart_agri.core.models.settings import FarmSettings


class ContractOperationsDashboardApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_superuser(
            username="contracts_superuser",
            email="contracts@example.com",
            password="pass1234",
        )
        self.client.force_authenticate(self.user)

        self.farm = Farm.objects.create(name="Contracts Farm", slug="contracts-farm", region="R1")
        FarmMembership.objects.create(user=self.user, farm=self.farm, role="Admin")
        self.crop = Crop.objects.create(name="Wheat", mode="Open")
        self.season = Season.objects.create(
            name="2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        self.settings = FarmSettings.objects.create(
            farm=self.farm,
            mode=FarmSettings.MODE_STRICT,
            cost_visibility=FarmSettings.COST_VISIBILITY_FULL,
            enable_sharecropping=True,
            sharecropping_mode=FarmSettings.SHARECROPPING_MODE_PHYSICAL,
            contract_mode=FarmSettings.CONTRACT_MODE_FULL_ERP,
            treasury_visibility=FarmSettings.TREASURY_VISIBILITY_VISIBLE,
        )

    def test_dashboard_aggregates_sharecropping_and_rental_contracts(self):
        share_contract = SharecroppingContract.objects.create(
            farm=self.farm,
            farmer_name="Partner Farmer",
            crop=self.crop,
            season=self.season,
            contract_type=SharecroppingContract.CONTRACT_TYPE_SHARECROPPING,
            irrigation_type=IrrigationType.WELL_PUMP,
            institution_percentage=Decimal("0.3000"),
        )
        assessment = TouringAssessment.objects.create(
            contract=share_contract,
            estimated_total_yield_kg=Decimal("1000.0000"),
            expected_zakat_kg=Decimal("50.0000"),
            expected_institution_share_kg=Decimal("300.0000"),
            committee_members=["A", "B", "C"],
            is_harvested=True,
        )
        SharecroppingReceipt.objects.create(
            farm=self.farm,
            assessment=assessment,
            receipt_type=SharecroppingReceipt.RECEIPT_TYPE_FINANCIAL,
            amount_received=Decimal("280.0000"),
            received_by=self.user,
            is_posted=True,
        )

        rental_contract = SharecroppingContract.objects.create(
            farm=self.farm,
            farmer_name="Rental Farmer",
            crop=self.crop,
            season=self.season,
            contract_type=SharecroppingContract.CONTRACT_TYPE_RENTAL,
            irrigation_type=IrrigationType.RAIN,
            institution_percentage=Decimal("0.2000"),
            annual_rent_amount=Decimal("900.0000"),
        )
        SharecroppingContract.objects.filter(pk=rental_contract.pk).update(
            created_at=timezone.now() - timedelta(days=45)
        )
        AuditLog.objects.create(
            actor=self.user,
            farm=self.farm,
            action="RENT_PAYMENT",
            model="SharecroppingContract",
            object_id=str(rental_contract.id),
            new_payload={
                "amount": "400.0000",
                "payment_period": "2026-Q1",
                "farm_id": self.farm.id,
            },
        )

        response = self.client.get("/api/v1/sharecropping-contracts/dashboard/", {"farm": self.farm.id})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["summary"]["total_contracts"], 2)
        self.assertEqual(payload["summary"]["mismatched_settlements"], 1)
        self.assertEqual(payload["summary"]["unresolved_contract_variances"], 2)

        rows = payload["results"]
        share_row = next(entry for entry in rows if entry["contract_type"] == "SHARECROPPING")
        rental_row = next(entry for entry in rows if entry["contract_type"] == "RENTAL")

        self.assertEqual(share_row["policy_snapshot"]["contract_mode"], FarmSettings.CONTRACT_MODE_FULL_ERP)
        self.assertEqual(share_row["touring_state"], "HARVESTED")
        self.assertEqual(share_row["receipt_state"], "POSTED_FINANCIAL")
        self.assertIn("posted_mode_mismatch", share_row["flags"])

        self.assertEqual(rental_row["settlement_state"], "PARTIAL")
        self.assertEqual(rental_row["last_rent_payment"]["payment_period"], "2026-Q1")
        self.assertEqual(rental_row["actual_institution_share"], "400.0000")

    def test_simple_mode_redacts_contract_amounts_but_keeps_posture(self):
        self.settings.mode = FarmSettings.MODE_SIMPLE
        self.settings.contract_mode = FarmSettings.CONTRACT_MODE_OPERATIONAL_ONLY
        self.settings.cost_visibility = FarmSettings.COST_VISIBILITY_RATIOS_ONLY
        self.settings.save(update_fields=["mode", "contract_mode", "cost_visibility"])

        rental_contract = SharecroppingContract.objects.create(
            farm=self.farm,
            farmer_name="Simple Rental",
            crop=self.crop,
            season=self.season,
            contract_type=SharecroppingContract.CONTRACT_TYPE_RENTAL,
            irrigation_type=IrrigationType.RAIN,
            institution_percentage=Decimal("0.2000"),
            annual_rent_amount=Decimal("900.0000"),
        )
        AuditLog.objects.create(
            actor=self.user,
            farm=self.farm,
            action="RENT_PAYMENT",
            model="SharecroppingContract",
            object_id=str(rental_contract.id),
            new_payload={
                "amount": "400.0000",
                "payment_period": "2026-Q1",
                "farm_id": self.farm.id,
            },
        )

        response = self.client.get("/api/v1/sharecropping-contracts/dashboard/", {"farm": self.farm.id})
        self.assertEqual(response.status_code, 200)
        row = response.json()["results"][0]
        self.assertTrue(row["amounts_redacted"])
        self.assertEqual(row["economic_posture"], "PARTIAL")
        self.assertIsNone(row["annual_rent_amount"])
        self.assertIsNone(row["actual_institution_share"])

    def test_record_rent_payment_respects_contract_policy_gate(self):
        contract = SharecroppingContract.objects.create(
            farm=self.farm,
            farmer_name="Rental Farmer",
            crop=self.crop,
            season=self.season,
            contract_type=SharecroppingContract.CONTRACT_TYPE_RENTAL,
            irrigation_type=IrrigationType.RAIN,
            institution_percentage=Decimal("0.2000"),
            annual_rent_amount=Decimal("900.0000"),
        )

        self.settings.contract_mode = FarmSettings.CONTRACT_MODE_OPERATIONAL_ONLY
        self.settings.mode = FarmSettings.MODE_STRICT
        self.settings.save(update_fields=["contract_mode", "mode"])

        blocked = self.client.post(
            f"/api/v1/sharecropping-contracts/{contract.id}/record-rent-payment/",
            {"amount": "100.0000", "payment_period": "2026-Q1"},
            HTTP_X_IDEMPOTENCY_KEY="rent-blocked-q1",
            format="json",
        )
        self.assertEqual(blocked.status_code, 403)

        self.settings.contract_mode = FarmSettings.CONTRACT_MODE_FULL_ERP
        self.settings.save(update_fields=["contract_mode"])

        posted = self.client.post(
            f"/api/v1/sharecropping-contracts/{contract.id}/record-rent-payment/",
            {"amount": "100.0000", "payment_period": "2026-Q1", "notes": "Board-approved"},
            HTTP_X_IDEMPOTENCY_KEY="rent-posted-q1",
            format="json",
        )
        self.assertEqual(posted.status_code, 200)
        self.assertEqual(posted.json()["status"], "posted")
        self.assertTrue(
            AuditLog.objects.filter(
                action="RENT_PAYMENT",
                object_id=str(contract.id),
                new_payload__payment_period="2026-Q1",
            ).exists()
        )
