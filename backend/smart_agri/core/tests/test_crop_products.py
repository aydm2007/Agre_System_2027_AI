from django.contrib.auth.models import Group, User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models import (
    Asset,
    Crop,
    CropProduct,
    Farm,
    FarmCrop,
    Item,
    Location,
    Task,
)


class CropProductAPITests(APITestCase):
    def setUp(self):
        self.manager = User.objects.create_user('manager_crop_products', password='pass', is_staff=True)
        manager_group, _ = Group.objects.get_or_create(name='Manager')
        self.manager.groups.add(manager_group)

        self.farm = Farm.objects.create(name='Farm Alpha', slug='farm-alpha', region='A')
        FarmMembership.objects.create(user=self.manager, farm=self.farm, role='Manager')

        self.crop = Crop.objects.create(name='Date Palm', mode='Open')
        FarmCrop.objects.create(farm=self.farm, crop=self.crop)

        self.item_primary = Item.objects.create(name='Grade A Dates', group='Harvested Product', uom='kg')
        self.item_secondary = Item.objects.create(name='Grade B Dates', group='Harvested Product', uom='kg')

        self.client = APIClient()
        self.client.force_authenticate(self.manager)

    def test_item_endpoint_filters_by_crop(self):
        CropProduct.objects.create(crop=self.crop, item=self.item_primary, is_primary=True)
        other_item = Item.objects.create(name='Olive Oil', group='Harvested Product', uom='L')

        url = reverse('items-list')
        response = self.client.get(url, {'crop': self.crop.id, 'group': 'Harvested Product'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data.get('results', response.data)
        item_ids = {entry['id'] for entry in results}
        self.assertIn(self.item_primary.id, item_ids)
        self.assertNotIn(other_item.id, item_ids)

    def test_primary_product_is_exclusive(self):
        first_link = CropProduct.objects.create(crop=self.crop, item=self.item_primary, is_primary=True)
        second_link = CropProduct.objects.create(crop=self.crop, item=self.item_secondary, is_primary=True)

        first_link.refresh_from_db()
        second_link.refresh_from_db()

        self.assertFalse(first_link.is_primary)
        self.assertTrue(second_link.is_primary)

    def test_crop_cards_endpoint_returns_services_and_products(self):
        CropProduct.objects.create(crop=self.crop, item=self.item_primary, is_primary=True)

        location = Location.objects.create(farm=self.farm, name='Block 1', type='Field')
        Asset.objects.create(farm=self.farm, category='Machinery', name='Tractor 1')
        Task.objects.create(
            crop=self.crop,
            stage='Irrigation',
            name='Drip cycle',
            requires_machinery=True,
            is_asset_task=True,
            asset_type='machinery',
        )

        url = reverse('crop-cards-list')
        response = self.client.get(url, {'farm_id': self.farm.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(isinstance(response.data, list))
        self.assertEqual(len(response.data), 1)

        card = response.data[0]
        self.assertEqual(card['id'], self.crop.id)
        self.assertEqual(card['farms'][0]['id'], self.farm.id)
        self.assertTrue(any(product['item_id'] == self.item_primary.id for product in card['products']))
        self.assertTrue(any(service['name'] == 'Drip cycle' for service in card['services']))
