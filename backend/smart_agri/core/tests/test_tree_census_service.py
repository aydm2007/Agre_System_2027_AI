from datetime import date
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase

from smart_agri.core.models import Crop, DailyLog, Farm, Location
from smart_agri.core.models.inventory import (
    BiologicalAssetCohort,
    BiologicalAssetTransaction,
    TreeCensusVarianceAlert,
)
from smart_agri.core.services.tree_census_service import TreeCensusService


class TreeCensusServiceTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.actor = user_model.objects.create_user(
            username=f"tree-{uuid4().hex[:8]}",
            password="pass1234",
            is_superuser=True,
        )
        suffix = uuid4().hex[:8]
        self.farm = Farm.objects.create(name=f"Farm {suffix}", slug=f"farm-{suffix}", region="R1")
        self.location = Location.objects.create(farm=self.farm, name=f"Loc {suffix}")
        self.crop = Crop.objects.create(name=f"Crop {suffix}", mode="Open", is_perennial=True)
        self.log = DailyLog.objects.create(farm=self.farm, log_date=date.today())

    def _build_alert_and_cohort(self, *, quantity: int, missing_quantity: int, status: str):
        cohort = BiologicalAssetCohort.objects.create(
            farm=self.farm,
            location=self.location,
            crop=self.crop,
            batch_name=f"Batch {uuid4().hex[:6]}",
            quantity=quantity,
            status=status,
            planted_date=date.today(),
        )
        alert = TreeCensusVarianceAlert.objects.create(
            log=self.log,
            farm=self.farm,
            location=self.location,
            crop=self.crop,
            missing_quantity=missing_quantity,
            reason="Test variance",
        )
        return cohort, alert

    def test_partial_loss_keeps_transaction_to_status_equal_original(self):
        cohort, alert = self._build_alert_and_cohort(
            quantity=10,
            missing_quantity=3,
            status=BiologicalAssetCohort.STATUS_PRODUCTIVE,
        )

        TreeCensusService.resolve_variance_alert(
            alert=alert,
            cohort_id=cohort.id,
            actor=self.actor,
        )

        cohort.refresh_from_db()
        tx = BiologicalAssetTransaction.objects.get(reference_id=f"variance-alert-{alert.pk}")
        self.assertEqual(cohort.quantity, 7)
        self.assertEqual(cohort.status, BiologicalAssetCohort.STATUS_PRODUCTIVE)
        self.assertEqual(tx.from_status, BiologicalAssetCohort.STATUS_PRODUCTIVE)
        self.assertEqual(tx.to_status, BiologicalAssetCohort.STATUS_PRODUCTIVE)

    def test_full_loss_sets_transaction_and_cohort_to_excluded(self):
        cohort, alert = self._build_alert_and_cohort(
            quantity=4,
            missing_quantity=4,
            status=BiologicalAssetCohort.STATUS_PRODUCTIVE,
        )

        TreeCensusService.resolve_variance_alert(
            alert=alert,
            cohort_id=cohort.id,
            actor=self.actor,
        )

        cohort.refresh_from_db()
        tx = BiologicalAssetTransaction.objects.get(reference_id=f"variance-alert-{alert.pk}")
        self.assertEqual(cohort.quantity, 0)
        self.assertEqual(cohort.status, BiologicalAssetCohort.STATUS_EXCLUDED)
        self.assertEqual(tx.from_status, BiologicalAssetCohort.STATUS_PRODUCTIVE)
        self.assertEqual(tx.to_status, BiologicalAssetCohort.STATUS_EXCLUDED)
