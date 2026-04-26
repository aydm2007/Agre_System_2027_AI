"""
Operational Contracts Audit Tests (Phase 8.2 Image Checklist)
=============================================================
Proves:
1. Touring = assessment-only (No financial ledger impact)
2. Sharecropping separation (Physical harvest vs Financial settlement)
3. Link contracts to harvest/production
"""

from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase

from smart_agri.core.models import Activity, Farm
from smart_agri.core.models.crop import Crop
from smart_agri.core.models.partnerships import SharecroppingContract
from smart_agri.core.models.planning import CropPlan
from smart_agri.finance.models import FinancialLedger


class OperationalContractsGovernanceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="contract_user")
        self.farm = Farm.objects.create(
            name="Contract Farm",
            slug="contract-farm",
            area=Decimal("100"),
            region="HQ",
        )
        self.crop = Crop.objects.create(name="Wheat")
        self.plan = CropPlan.objects.create(farm=self.farm, season="Winter", crop=self.crop)

        self.season = self.plan.season
        self.contract = SharecroppingContract.objects.create(
            farm=self.farm,
            farmer_name="Test Partner",
            contract_type=SharecroppingContract.CONTRACT_TYPE_SHARECROPPING,
            institution_percentage=Decimal("0.5000"),
            irrigation_type="RAIN",
            crop=self.crop,
            season=self.season,
        )

    def test_touring_is_assessment_only(self):
        """
        Prove 'touring = assessment-only' (No financial impact).
        Touring records field condition but MUST NOT debit/credit the General Ledger directly.
        """
        from smart_agri.core.services.touring_harvest_service import TouringHarvestService

        ledger_count_before = FinancialLedger.objects.count()

        assessment = TouringHarvestService.execute_touring_assessment(
            contract_id=self.contract.id,
            estimated_kg=Decimal("10500.00"),
            committee=["Member A", "Member B", "Member C"],
        )

        ledger_count_after = FinancialLedger.objects.count()

        self.assertIsNotNone(assessment.id)
        self.assertEqual(assessment.contract_id, self.contract.id)
        self.assertEqual(
            ledger_count_after,
            ledger_count_before,
            "Touring must be assessment-only and not produce ledger entries.",
        )

    def test_sharecropping_physical_vs_financial_isolation(self):
        """
        Prove 'sharecropping' physical vs financial separation.
        A physical harvest against a sharecropping contract increases inventory
        but does not trigger financial settlement/liability until the settlement cycle.
        """
        from smart_agri.core.services.touring_harvest_service import TouringHarvestService

        self.contract.contract_type = "SHARECROPPING"
        self.contract.save()

        TouringHarvestService.execute_touring_assessment(
            contract_id=self.contract.id,
            estimated_kg=Decimal("1000.00"),
            committee=["Member A", "Member B", "Member C"],
        )

        ledger_count_before = FinancialLedger.objects.count()

        harvest_result = TouringHarvestService.execute_sharecropping_harvest(
            contract_id=self.contract.id,
            actual_total_kg=Decimal("1000.00"),
            yield_type="IN_KIND",
            committee=["Member A", "Member B", "Member C"],
        )

        ledger_count_after = FinancialLedger.objects.count()

        self.assertEqual(harvest_result["status"], "success")
        self.assertIsNotNone(harvest_result["receipt_id"])
        self.assertEqual(
            ledger_count_after,
            ledger_count_before,
            "Physical harvest for sharecropping must not hit financial ledger directly.",
        )

    def test_contracts_linked_to_harvest_and_production(self):
        """
        Prove linkage between contracts and harvest/production truth.
        """
        from smart_agri.core.models.partnerships import SharecroppingReceipt
        from smart_agri.core.services.touring_harvest_service import TouringHarvestService

        TouringHarvestService.execute_touring_assessment(
            contract_id=self.contract.id,
            estimated_kg=Decimal("500.00"),
            committee=["Member A", "Member B", "Member C"],
        )
        harvest_result = TouringHarvestService.execute_sharecropping_harvest(
            contract_id=self.contract.id,
            actual_total_kg=Decimal("500.00"),
            yield_type="IN_KIND",
            committee=["Member A", "Member B", "Member C"],
        )

        receipt = SharecroppingReceipt.objects.get(id=harvest_result["receipt_id"])
        self.assertEqual(receipt.assessment.contract_id, self.contract.id)
        self.assertIsNotNone(receipt.assessment.contract)

    def test_sharecropping_does_not_create_technical_activities(self):
        """[M4.2] Sharecropping is a contract workflow and must not generate technical activities."""
        activities_before = Activity.objects.count()

        from smart_agri.core.services.touring_harvest_service import TouringHarvestService

        TouringHarvestService.execute_touring_assessment(
            contract_id=self.contract.id,
            estimated_kg=Decimal("100.00"),
            committee=["Member A", "Member B", "Member C"],
        )

        activities_after = Activity.objects.count()
        self.assertEqual(
            activities_before,
            activities_after,
            "Sharecropping execution must not generate technical Activity rows natively.",
        )

    def test_contract_settlement_respects_profiled_posting(self):
        """[M4.2] Contract cash settlements must obey strict_finance profiled posting policies."""
        from smart_agri.core.models.settings import FarmSettings
        from smart_agri.finance.services.farm_finance_authority_service import (
            FarmFinanceAuthorityService,
        )

        FarmSettings.objects.create(
            farm=self.farm,
            mode=FarmSettings.MODE_STRICT,
            approval_profile=FarmSettings.APPROVAL_PROFILE_STRICT_FINANCE,
        )

        with patch.object(FarmFinanceAuthorityService, "require_sector_final_authority") as mock_auth:
            FarmFinanceAuthorityService.require_profiled_posting_authority(
                user=self.user,
                farm=self.farm,
                action_label="contract settlement posting",
            )

        mock_auth.assert_called_once_with(
            user=self.user,
            farm=self.farm,
            action_label="contract settlement posting",
        )
