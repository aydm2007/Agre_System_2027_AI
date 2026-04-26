from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models import Farm, Crop, FarmCrop, Item, Unit


class UnitAndMaterialAPITests(APITestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='unit_admin',
            email='unit_admin@example.com',
            password='pass1234',
        )
        self.client = APIClient()
        self.client.force_authenticate(self.superuser)

        self.farm = Farm.objects.create(name='Test Farm', slug='test-farm', region='Central')
        FarmMembership.objects.create(user=self.superuser, farm=self.farm, role='Admin')
        self.crop = Crop.objects.create(name='Test Crop', mode='Open')
        FarmCrop.objects.create(farm=self.farm, crop=self.crop)

    def test_create_unit_and_item_uses_unit_symbol(self):
        unit_payload = {
            'code': 'crate',
            'name': 'Crate',
            'symbol': 'crate',
            'category': 'count',
            'precision': 0,
        }
        unit_response = self.client.post(reverse('units-list'), unit_payload, format='json')
        self.assertEqual(unit_response.status_code, status.HTTP_201_CREATED)
        unit_id = unit_response.data['id']

        item_payload = {
            'name': 'Sample Product',
            'group': 'Harvested Product',
            'unit': unit_id,
        }
        item_response = self.client.post(reverse('items-list'), item_payload, format='json')
        self.assertEqual(item_response.status_code, status.HTTP_201_CREATED, item_response.data)
        self.assertEqual(item_response.data['unit'], unit_id)
        self.assertEqual(item_response.data['uom'], 'crate')

    def test_crop_material_accepts_recommended_unit(self):
        kilogram, _ = Unit.objects.get_or_create(
            code='kg',
            defaults={'name': 'Kilogram', 'symbol': 'kg', 'category': 'mass', 'precision': 3},
        )
        item = Item.objects.create(name='Nitrogen Mix', group='Fertilizer', uom='kg', unit=kilogram)

        material_payload = {
            'crop': self.crop.id,
            'item': item.id,
            'is_primary': True,
            'recommended_qty': '25.5',
            'recommended_unit': kilogram.id,
        }

        response = self.client.post(reverse('crop-materials-list'), material_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['recommended_unit'], kilogram.id)
        self.assertEqual(response.data['recommended_unit_detail']['symbol'], 'kg')
