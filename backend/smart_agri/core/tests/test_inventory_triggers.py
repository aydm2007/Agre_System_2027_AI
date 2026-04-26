from decimal import Decimal
from uuid import uuid4

from django.test import TestCase

from smart_agri.core.models import (
    Farm,
    Item,
    ItemInventory,
    ItemInventoryBatch,
    Location,
    StockMovement,
    Unit,
)


class InventorySignalsTests(TestCase):

    def setUp(self):
        self.farm = Farm.objects.create(name="Farm", slug="farm", region="A")
        self.location_a = Location.objects.create(farm=self.farm, name="Block A")
        self.location_b = Location.objects.create(farm=self.farm, name="Block B")
        unique_code = f"kg_{uuid4().hex[:8]}"
        self.unit = Unit.objects.create(code=unique_code, name="Kilogram", symbol="كغ", category=Unit.CATEGORY_MASS)
        self.item = Item.objects.create(name="Fertilizer", group="Inputs", uom="kg", unit=self.unit)

    def _create_movement(self, location, qty):
        return StockMovement.objects.create(
            farm=self.farm,
            item=self.item,
            location=location,
            qty_delta=Decimal(qty),
            ref_type="test",
            ref_id="ref-1",
            note="seed",
        )

    def test_stockmovement_updates_are_reflected(self):
        movement = self._create_movement(self.location_a, '10.0')

        inventory = ItemInventory.objects.get(farm=self.farm, location=self.location_a, item=self.item)
        self.assertEqual(inventory.qty, Decimal('10.0'))

        movement.qty_delta = Decimal('6.0')
        movement.save()

        inventory.refresh_from_db()
        self.assertEqual(inventory.qty, Decimal('6.0'))

        movement.location = self.location_b
        movement.save()

        inventory.refresh_from_db()
        self.assertEqual(inventory.qty, Decimal('0'))
        other_inventory = ItemInventory.objects.get(farm=self.farm, location=self.location_b, item=self.item)
        self.assertEqual(other_inventory.qty, Decimal('6.0'))

    def test_stockmovement_delete_rolls_back_inventory(self):
        movement = self._create_movement(self.location_a, '5.5')

        stock_record = ItemInventory.objects.get(farm=self.farm, location=self.location_a, item=self.item)
        self.assertEqual(stock_record.qty, Decimal('5.5'))
        self.assertTrue(ItemInventoryBatch.objects.filter(inventory=stock_record).exists())

        movement.delete()

        stock_record.refresh_from_db()
        self.assertEqual(stock_record.qty, Decimal('0'))
        batch = ItemInventoryBatch.objects.filter(inventory=stock_record).first()
        if batch:
            self.assertEqual(batch.qty, Decimal('0'))
