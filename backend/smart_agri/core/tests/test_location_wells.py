from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.test import TestCase
from rest_framework.test import APIClient

from smart_agri.accounts.models import FarmMembership
from decimal import Decimal

from smart_agri.core.models import Asset, Farm, Location, LocationWell


class LocationWellAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user("manager", password="pass123")
        manager_group, _ = Group.objects.get_or_create(name="Manager")
        self.user.groups.add(manager_group)
        self.client.force_authenticate(self.user)

        self.farm = Farm.objects.create(name="Farm Alpha", slug="farm-alpha", region="North")
        FarmMembership.objects.create(user=self.user, farm=self.farm, role="Manager")

        self.location = Location.objects.create(farm=self.farm, name="Field 1")
        self.asset = Asset.objects.create(farm=self.farm, category="Well", name="Main Well")

        self.other_farm = Farm.objects.create(name="Farm Beta", slug="farm-beta", region="South")
        self.other_location = Location.objects.create(farm=self.other_farm, name="Field 2")
        self.other_asset = Asset.objects.create(farm=self.other_farm, category="Well", name="Backup Well")

    def test_duplicate_link_returns_custom_validation_error(self):
        LocationWell.objects.create(location=self.location, asset=self.asset)

        payload = {
            "location_id": self.location.id,
            "asset_id": self.asset.id,
        }

        url = "/api/v1/location-wells/"

        with patch("smart_agri.core.api.LocationWellSerializer.get_validators", return_value=[]):
            response = self.client.post(
                url,
                payload,
                format="json",
                HTTP_X_IDEMPOTENCY_KEY="test-location-well-dup-create-1",
            )

        self.assertEqual(response.status_code, 400)

        data = response.json()
        self.assertIn("detail", data)

        detail = data["detail"]
        if isinstance(detail, list):
            self.assertIn("تم ربط هذا الموقع بالبئر مسبقًا.", detail)
        else:
            self.assertEqual(detail, "تم ربط هذا الموقع بالبئر مسبقًا.")

    def test_user_cannot_access_location_wells_from_other_farms(self):
        own_link = LocationWell.objects.create(location=self.location, asset=self.asset)
        # reuse the secondary farm/location/assets created in setUp
        forbidden_link = LocationWell.objects.create(location=self.other_location, asset=self.other_asset)

        restricted_user = User.objects.create_user("viewer", password="pass123")
        FarmMembership.objects.create(user=restricted_user, farm=self.farm, role="Viewer")

        self.client.force_authenticate(restricted_user)

        list_response = self.client.get("/api/v1/location-wells/")
        self.assertEqual(list_response.status_code, 200)

        payload = list_response.json()
        if isinstance(payload, dict) and "results" in payload:
            records = payload["results"]
        else:
            records = payload
        self.assertIsInstance(records, list)
        returned_ids = {item.get("id") for item in records}

        self.assertIn(own_link.id, returned_ids)
        self.assertNotIn(forbidden_link.id, returned_ids)

        detail_url = f"/api/v1/location-wells/{forbidden_link.id}/"
        detail_response = self.client.get(detail_url)
        self.assertEqual(detail_response.status_code, 403)

    def test_update_operational_fields(self):
        link = LocationWell.objects.create(location=self.location, asset=self.asset)

        payload = {
            'depth_meters': Decimal('120.5'),
            'water_level_meters': Decimal('45.2'),
            'discharge_rate_lps': Decimal('11.7'),
            'status': 'maintenance',
            'last_serviced_at': '2025-10-10',
            'notes': 'تغيير مضخة',
        }

        response = self.client.patch(
            f"/api/v1/location-wells/{link.id}/",
            payload,
            format='json',
            HTTP_X_IDEMPOTENCY_KEY="test-location-well-update-1",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'maintenance')
        self.assertEqual(data['notes'], 'تغيير مضخة')
        self.assertEqual(data['last_serviced_at'], '2025-10-10')

        link.refresh_from_db()
        self.assertEqual(link.depth_meters, payload['depth_meters'])
        self.assertEqual(link.discharge_rate_lps, payload['discharge_rate_lps'])

    def test_summary_endpoint_limits_scope(self):
        LocationWell.objects.create(location=self.location, asset=self.asset)
        LocationWell.objects.create(location=self.other_location, asset=self.other_asset)

        response = self.client.get(f"/api/v1/location-wells/summary/?farm_id={self.farm.id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['total'], 1)
        status_entry = next((item for item in data['by_status'] if item['status'] == 'active'), None)
        self.assertIsNotNone(status_entry)
        self.assertEqual(status_entry['count'], 1)

    def test_location_wells_farm_filter_no_field_error(self):
        """
        Regression guard:
        relation-scoped endpoint must accept `farm_id` without trying to filter by a non-existent direct field.
        """
        LocationWell.objects.create(location=self.location, asset=self.asset)
        response = self.client.get(f"/api/v1/location-wells/?farm_id={self.farm.id}")
        self.assertEqual(response.status_code, 200)

    def test_location_wells_farm_filter_returns_scoped_rows(self):
        own_link = LocationWell.objects.create(location=self.location, asset=self.asset)
        LocationWell.objects.create(location=self.other_location, asset=self.other_asset)

        response = self.client.get(f"/api/v1/location-wells/?farm_id={self.farm.id}")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        records = payload.get("results", payload) if isinstance(payload, dict) else payload
        returned_ids = {item.get("id") for item in records}
        self.assertIn(own_link.id, returned_ids)
        self.assertEqual(len(returned_ids), 1)
