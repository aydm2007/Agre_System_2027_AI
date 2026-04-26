from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models import (
    Crop,
    Farm,
    FarmCrop,
    Unit,
    Item,
    CropMaterial,
    DailyLog,
    Activity,
    ActivityItem,
    UnitConversion,
    CropTemplate,
    CropTemplateMaterial,
    CropTemplateTask,
    ItemInventory,
)


class CatalogEnhancementTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_superuser('catalog_admin', 'admin@example.com', 'pass1234')
        self.client = APIClient()
        self.client.force_authenticate(self.user)

        self.farm = Farm.objects.create(name='Test Farm', slug='test-farm', region='A')
        FarmMembership.objects.create(user=self.user, farm=self.farm, role='Admin')

        self.crop = Crop.objects.create(name='Tomato', mode='Open')
        FarmCrop.objects.create(farm=self.farm, crop=self.crop)

        self.kg, _ = Unit.objects.get_or_create(code='kg', defaults={'name': 'Kilogram', 'symbol': 'kg', 'category': 'mass'})
        self.g, _ = Unit.objects.get_or_create(code='g', defaults={'name': 'Gram', 'symbol': 'g', 'category': 'mass'})

        self.item = Item.objects.create(name='NPK Fertiliser', group='Fertilizer', uom='kg', unit=self.kg, unit_price=10, currency='SAR', reorder_level=50)
        CropMaterial.objects.create(crop=self.crop, item=self.item, recommended_qty=Decimal('25'), recommended_unit=self.kg)

        self.log = DailyLog.objects.create(farm=self.farm, log_date=date.today())
        self.activity = Activity.objects.create(log=self.log, crop=self.crop, days_spent=1)
        ActivityItem.objects.create(activity=self.activity, item=self.item, qty=Decimal('5'), uom='kg')

        ItemInventory.objects.create(farm=self.farm, item=self.item, qty=Decimal('10'), uom='kg')

    def test_unit_conversion_creates_reciprocal(self):
        url = reverse('unit-conversions-list')
        response = self.client.post(url, {
            'from_unit': self.kg.id,
            'to_unit': self.g.id,
            'multiplier': '1000',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        direct = UnitConversion.objects.get(from_unit=self.kg, to_unit=self.g)
        reciprocal = UnitConversion.objects.get(from_unit=self.g, to_unit=self.kg)
        self.assertEqual(direct.multiplier, Decimal('1000'))
        self.assertEqual(reciprocal.multiplier.quantize(Decimal('0.001')), Decimal('0.001'))

    def test_resource_analytics_returns_costs(self):
        url = reverse('resource-analytics-list')
        response = self.client.get(url, {'farm': self.farm.id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data['results']
        self.assertEqual(len(payload), 1)
        crop_entry = payload[0]
        self.assertEqual(crop_entry['crop']['id'], self.crop.id)
        material_entry = crop_entry['materials'][0]
        self.assertAlmostEqual(material_entry['recommended_cost'], 250.0)
        self.assertAlmostEqual(material_entry['actual_cost'], 50.0)

    def test_crop_template_endpoints(self):
        template_url = reverse('crop-templates-list')
        template_resp = self.client.post(template_url, {
            'crop': self.crop.id,
            'name': 'Basal Nutrition',
            'category': 'bundle',
            'description': 'Base fertiliser plan',
        }, format='json')
        self.assertEqual(template_resp.status_code, status.HTTP_201_CREATED)
        template_id = template_resp.data['id']

        material_url = reverse('crop-template-materials-list')
        mat_resp = self.client.post(material_url, {
            'template': template_id,
            'item': self.item.id,
            'qty': '12.5',
            'unit': self.kg.id,
        }, format='json')
        self.assertEqual(mat_resp.status_code, status.HTTP_201_CREATED)

        task_url = reverse('crop-template-tasks-list')
        task_resp = self.client.post(task_url, {
            'template': template_id,
            'name': 'Apply fertiliser',
            'stage': 'Nutrition',
            'estimated_hours': '2.5',
        }, format='json')
        self.assertEqual(task_resp.status_code, status.HTTP_201_CREATED)

        detail_resp = self.client.get(f"{template_url}{template_id}/")
        self.assertEqual(detail_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(detail_resp.data['materials']), 1)
        self.assertEqual(len(detail_resp.data['tasks']), 1)

    def test_item_inventory_low_stock_flag(self):
        url = reverse('item-inventories-list')
        response = self.client.get(url, {'farm': self.farm.id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        self.assertTrue(results[0]['low_stock'])
