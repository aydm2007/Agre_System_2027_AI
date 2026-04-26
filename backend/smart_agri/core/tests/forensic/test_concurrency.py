import pytest
from decimal import Decimal
from django.db import transaction, IntegrityError
from django.test import TransactionTestCase
import concurrent.futures

from smart_agri.core.models import Farm, Location, Item, ItemInventory
from smart_agri.core.services.inventory_service import InventoryService


class InventoryConcurrencyTest(TransactionTestCase):
    
    def setUp(self):
        self.farm = Farm.objects.create(name="Test Farm", code="TF001")
        self.item = Item.objects.create(name="Seeds", group="Input", uom="kg", unit_price=10)
        self.location = Location.objects.create(farm=self.farm, name="Barn A")
        
        # Initial Stock
        InventoryService.record_movement(
            farm=self.farm,
            item=self.item,
            location=self.location,
            qty_delta=Decimal("100.00"),
            note="Initial"
        )

    def test_concurrent_deductions(self):
        """
        Verify that parallel withdrawals do not cause race conditions.
        """
        def withdraw():
            try:
                InventoryService.record_movement(
                    farm=self.farm,
                    item=self.item,
                    location=self.location,
                    qty_delta=Decimal("-10.00"),
                    note="Parallel Withdraw"
                )
                return True
            except Exception as e:
                return e

        # Use ThreadPool to simulate loose parallelism (limit of SQLite/testing env)
        # In a real DB like Postgres, this tests row locking.
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(withdraw) for _ in range(10)]
            results = [f.result() for f in futures]

        # Check final stock
        final_stock = InventoryService.get_stock_level(self.farm, self.item, self.location)
        
        # We started with 100, withdrew 10 * 10 = 100. Should be 0.
        self.assertEqual(final_stock, Decimal("0.00"))
        
        # Verify no errors
        for res in results:
            self.assertTrue(res is True, f"Error in thread: {res}")

    def test_prevent_negative_inventory_race(self):
        """
        Verify that we cannot withdraw more than available even with concurrency.
        """
        # Start with 50
        InventoryService.record_movement(
            farm=self.farm,
            item=self.item,
            location=self.location,
            qty_delta=Decimal("-50.00"), # 100 - 50 = 50 remain
            note="Reduce to 50"
        )
        
        def withdraw_lot():
            # Try to withdraw 20. 
            # 3 threads * 20 = 60 > 50. One should fail.
            try:
                InventoryService.record_movement(
                    farm=self.farm,
                    item=self.item,
                    location=self.location,
                    qty_delta=Decimal("-20.00"),
                    note="Race Withdraw"
                )
                return "Success"
            except (ValueError, IntegrityError) as e:
                return "Blocked"
            except Exception as e:
                return f"Error: {e}"

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(withdraw_lot) for _ in range(3)]
            results = [f.result() for f in futures]
            
        success_count = results.count("Success")
        blocked_count = results.count("Blocked")
        
        # Should succeed exactly twice (20+20=40), 10 left. 3rd tries 20 -> fails.
        self.assertEqual(success_count, 2)
        self.assertEqual(blocked_count, 1)
        
        final_stock = InventoryService.get_stock_level(self.farm, self.item, self.location)
        self.assertEqual(final_stock, Decimal("10.00"))
