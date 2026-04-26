from django.test import TestCase
from smart_agri.inventory.models import Item, Unit, MaterialType

class MaterialTypeTests(TestCase):
    def test_item_material_type_default(self):
        """Item.material_type defaults to OTHER."""
        unit = Unit.objects.create(code="KG", name="كيلو", category="mass")
        item = Item.objects.create(name="سماد يوريا", group="أسمدة", unit=unit)
        self.assertEqual(item.material_type, MaterialType.OTHER)
    
    def test_item_material_type_fertilizer(self):
        """Item can be classified as FERTILIZER."""
        unit = Unit.objects.create(code="KG2", name="كيلو", category="mass")
        item = Item.objects.create(
            name="سماد NPK",
            group="أسمدة",
            material_type=MaterialType.FERTILIZER,
            unit=unit,
        )
        self.assertEqual(item.material_type, MaterialType.FERTILIZER)
        self.assertEqual(item.get_material_type_display(), "أسمدة")
    
    def test_item_unit_display(self):
        """Item.unit provides structured unit data."""
        unit = Unit.objects.create(code="LTR", name="لتر", symbol="ل", category="volume")
        item = Item.objects.create(name="مبيد حشري", unit=unit, material_type="PESTICIDE")
        self.assertEqual(item.unit.symbol, "ل")
        self.assertEqual(item.unit.category, "volume")
