from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from smart_agri.core.models import Crop, CropVariety, Farm, FarmCrop, LaborRate, Location, LocationTreeStock


class SeedTreeInventoryEndpointTests(APITestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username="seed-admin",
            email="seed-admin@example.com",
            password="pass1234",
        )
        self.client.force_authenticate(self.admin)

        self.farm = Farm.objects.create(name="Seed Farm", slug="seed-farm", region="North")
        self.location = Location.objects.create(
            farm=self.farm,
            name="Seed Orchard",
            type="Orchard",
        )
        self.crop = Crop.objects.create(
            name="محصول معمّر إثباتي",
            mode="Open",
            is_perennial=True,
        )
        FarmCrop.objects.create(farm=self.farm, crop=self.crop)

    def test_seed_endpoint_creates_proof_variety_and_location_stock_for_gap_crop(self):
        response = self.client.post("/api/v1/seed-tree-inventory/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        proof_variety = CropVariety.objects.filter(
            crop=self.crop,
            deleted_at__isnull=True,
        ).first()
        self.assertIsNotNone(proof_variety)
        self.assertIn("Proof Variety", proof_variety.name)

        stock = LocationTreeStock.objects.filter(
            location=self.location,
            crop_variety=proof_variety,
            deleted_at__isnull=True,
        ).first()
        self.assertIsNotNone(stock)
        self.assertGreater(stock.current_tree_count, 0)

        labor_rate = LaborRate.objects.filter(
            farm=self.farm,
            deleted_at__isnull=True,
        ).first()
        self.assertIsNotNone(labor_rate)
        self.assertGreater(labor_rate.daily_rate, 0)
