from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from smart_agri.core.models import Farm, Item, Location
from smart_agri.core.services.stock_adjustment import StockAdjustmentService

class StockAdjustmentTest(TestCase):
    def setUp(self):
        self.creator = User.objects.create_user(username='creator', password='pwd')
        self.approver = User.objects.create_user(username='approver', password='pwd')
        self.farm = Farm.objects.create(name="Test Farm")
        self.location = Location.objects.create(name="Store 1", farm=self.farm)
        self.item = Item.objects.create(name="Test Item 1", unit_price=10)

    def test_self_approval_loss_blocked(self):
        """Protocol XIII: Creator cannot approve their own loss."""
        with self.assertRaises(PermissionDenied):
            StockAdjustmentService.record_loss(
                self.farm, self.item, -5, self.location, 
                " Theft", self.creator, self.creator # Self-Approval
            )

    def test_proper_approval_loss_allowed(self):
        """Protocol XIII: Independent approver logic works."""
        StockAdjustmentService.record_loss(
            self.farm, self.item, -5, self.location, 
            "Theft", self.creator, self.approver # Proper Approval
        )
        self.assertTrue(True) # Should not raise
