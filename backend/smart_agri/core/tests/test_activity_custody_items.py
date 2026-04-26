from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models import Crop, DailyLog, Farm, Location, Supervisor, Task
from smart_agri.core.services.custody_transfer_service import CustodyTransferService
from smart_agri.finance.models import FinancialLedger
from smart_agri.inventory.models import Item, ItemInventory, StockMovement


class ActivityCustodyItemTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user("custody-manager", password="pass", is_staff=True)
        manager_group, _ = Group.objects.get_or_create(name="Manager")
        self.user.groups.add(manager_group)
        self.client.force_authenticate(self.user)

        self.farm = Farm.objects.create(name="Activity Farm", slug="activity-farm", region="North")
        FarmMembership.objects.create(user=self.user, farm=self.farm, role="Manager")
        self.supervisor = Supervisor.objects.create(farm=self.farm, name="Ahmed", code="SUP-2")
        self.field_location = Location.objects.create(farm=self.farm, name="Block 1", code="FIELD-1", type="Field")
        self.source_location = Location.objects.create(
            farm=self.farm,
            name="Main Warehouse",
            code="WAREHOUSE-1",
            type="Warehouse",
        )
        self.crop = Crop.objects.create(name="Mango", mode="Open")
        self.task = Task.objects.create(crop=self.crop, stage="Care", name="Fertilization", requires_tree_count=False)
        self.log = DailyLog.objects.create(
            farm=self.farm,
            log_date=timezone.localdate(),
            supervisor=self.supervisor,
        )
        self.item = Item.objects.create(name="Urea Activity", group="fertilizer", uom="kg", unit_price=Decimal("10.000"))
        ItemInventory.objects.create(
            farm=self.farm,
            location=self.source_location,
            item=self.item,
            qty=Decimal("10.000"),
            uom="kg",
        )
        self.activities_url = "/api/v1/activities/"

    def _accept_custody(self, qty="5"):
        transfer = CustodyTransferService.issue_transfer(
            farm=self.farm,
            supervisor=self.supervisor,
            item=self.item,
            source_location=self.source_location,
            qty=qty,
            actor=self.user,
            idempotency_key=f"issue-{qty}",
        )
        return CustodyTransferService.accept_transfer(transfer=transfer, actor=self.user)

    def test_activity_items_consume_from_custody_and_split_wastage_cost(self):
        accepted = self._accept_custody("5")

        response = self.client.post(
            self.activities_url,
            {
                "log_id": self.log.id,
                "task_id": self.task.id,
                "location_ids": [self.field_location.id],
                "items": [
                    {
                        "item": self.item.id,
                        "qty": "3",
                        "applied_qty": "2",
                        "waste_qty": "1",
                        "waste_reason": "spill",
                        'uom': 'kg',
                    }
                ],
            },
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="activity-custody-1",
        )

        self.assertEqual(response.status_code, 201, response.content)
        activity_id = response.json()["id"]
        movement = StockMovement.objects.filter(ref_type="activity", ref_id=str(activity_id)).latest("id")
        self.assertEqual(movement.location_id, accepted.custody_location_id)
        self.assertEqual(movement.qty_delta, Decimal("-3.000"))

        custody_inventory = ItemInventory.objects.get(
            farm=self.farm,
            location=accepted.custody_location,
            item=self.item,
        )
        warehouse_inventory = ItemInventory.objects.get(
            farm=self.farm,
            location=self.source_location,
            item=self.item,
        )
        self.assertEqual(custody_inventory.qty, Decimal("2.000"))
        self.assertEqual(warehouse_inventory.qty, Decimal("5.000"))

        self.assertEqual(response.json()["cost_materials"], "20.0000")
        self.assertEqual(response.json()["cost_wastage"], "10.0000")
        self.assertTrue(
            FinancialLedger.objects.filter(
                activity_id=activity_id,
                account_code=FinancialLedger.ACCOUNT_WASTAGE_EXPENSE,
            ).exists()
        )

    def test_activity_creation_rejects_consumption_without_accepted_custody(self):
        response = self.client.post(
            self.activities_url,
            {
                "log_id": self.log.id,
                "task_id": self.task.id,
                "location_ids": [self.field_location.id],
                "items": [
                    {
                        "item": self.item.id,
                        "qty": "1",
                        'uom': 'kg',
                    }
                ],
            },
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="activity-custody-2",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(StockMovement.objects.filter(ref_type="activity").exists())
