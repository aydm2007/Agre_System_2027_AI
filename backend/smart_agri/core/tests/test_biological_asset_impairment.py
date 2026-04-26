from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from smart_agri.core.models import Crop, CropVariety, Farm, Location
from smart_agri.core.models.tree import BiologicalAssetImpairment, LocationTreeStock, TreeLossReason


class BiologicalAssetImpairmentTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        suffix = uuid4().hex[:8]
        self.user = user_model.objects.create_user(username=f"impair-{suffix}", password="pass1234")
        self.farm = Farm.objects.create(name=f"Impairment Farm {suffix}", slug=f"impairment-farm-{suffix}", region="R1")
        self.location = Location.objects.create(farm=self.farm, name=f"Orchard {suffix}", type="Orchard")
        self.crop = Crop.objects.create(name=f"Mango {suffix}", mode="Open", is_perennial=True)
        self.variety = CropVariety.objects.create(crop=self.crop, name=f"Variety {suffix}")
        self.loss_reason = TreeLossReason.objects.create(code=f"FROST-{suffix}", name_en="Frost", name_ar="صقيع")
        self.stock = LocationTreeStock.objects.create(
            location=self.location,
            crop_variety=self.variety,
            current_tree_count=100,
        )

    def test_valid_impairment_saves_when_authorized(self):
        impairment = BiologicalAssetImpairment.objects.create(
            farm=self.farm,
            location_tree_stock=self.stock,
            loss_reason=self.loss_reason,
            incident_date=date.today(),
            dead_tree_count=20,
            impairment_value=Decimal("2500.0000"),
            reported_by=self.user,
            authorized_by=self.user,
            is_posted=True,
            idempotency_key=f"imp-{uuid4().hex}",
        )

        self.assertTrue(impairment.is_posted)
        self.assertEqual(impairment.dead_tree_count, 20)

    def test_rejects_dead_tree_count_above_available_stock(self):
        impairment = BiologicalAssetImpairment(
            farm=self.farm,
            location_tree_stock=self.stock,
            loss_reason=self.loss_reason,
            incident_date=date.today(),
            dead_tree_count=101,
            impairment_value=Decimal("3000.0000"),
            reported_by=self.user,
            idempotency_key=f"imp-{uuid4().hex}",
        )

        with self.assertRaises(ValidationError):
            impairment.full_clean()

    def test_rejects_cross_farm_stock_reference(self):
        other_farm = Farm.objects.create(name=f"Other Farm {uuid4().hex[:6]}", slug=f"other-farm-{uuid4().hex[:6]}", region="R2")
        impairment = BiologicalAssetImpairment(
            farm=other_farm,
            location_tree_stock=self.stock,
            loss_reason=self.loss_reason,
            incident_date=date.today(),
            dead_tree_count=10,
            impairment_value=Decimal("500.0000"),
            reported_by=self.user,
            idempotency_key=f"imp-{uuid4().hex}",
        )

        with self.assertRaises(ValidationError):
            impairment.full_clean()

    def test_requires_authorization_before_posting(self):
        impairment = BiologicalAssetImpairment(
            farm=self.farm,
            location_tree_stock=self.stock,
            loss_reason=self.loss_reason,
            incident_date=date.today(),
            dead_tree_count=10,
            impairment_value=Decimal("500.0000"),
            reported_by=self.user,
            is_posted=True,
            idempotency_key=f"imp-{uuid4().hex}",
        )

        with self.assertRaises(ValidationError):
            impairment.full_clean()
