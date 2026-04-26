from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from smart_agri.core.models import Farm, Location, Supervisor
from smart_agri.core.services.custody_transfer_service import CustodyTransferService
from smart_agri.inventory.models import Item, ItemInventory


class CustodyTransferServiceTests(TestCase):
    def setUp(self):
        self.actor = User.objects.create_user("custody-actor", password="pass")
        self.farm = Farm.objects.create(name="Custody Farm", slug="custody-farm", region="North")
        self.supervisor = Supervisor.objects.create(farm=self.farm, name="Ahmed", code="SUP-1")
        self.source_location = Location.objects.create(
            farm=self.farm,
            name="Main Warehouse",
            code="MAIN-WH",
            type="Warehouse",
        )
        self.item = Item.objects.create(name="Urea", group="fertilizer", uom="kg", unit_price=Decimal("10.000"))
        ItemInventory.objects.create(
            farm=self.farm,
            location=self.source_location,
            item=self.item,
            qty=Decimal("10.000"),
            uom="kg",
        )

    def test_issue_accept_and_partial_return_lifecycle(self):
        transfer = CustodyTransferService.issue_transfer(
            farm=self.farm,
            supervisor=self.supervisor,
            item=self.item,
            source_location=self.source_location,
            qty="5",
            actor=self.actor,
            idempotency_key="custody-issue-1",
        )
        self.assertEqual(transfer.status, transfer.STATUS_ISSUED_PENDING_ACCEPTANCE)
        self.assertEqual(
            CustodyTransferService.get_item_custody_balance(
                farm=self.farm,
                supervisor=self.supervisor,
                item=self.item,
            ),
            Decimal("0.000"),
        )

        transfer = CustodyTransferService.accept_transfer(transfer=transfer, actor=self.actor)
        self.assertEqual(transfer.status, transfer.STATUS_ACCEPTED)
        self.assertEqual(
            CustodyTransferService.get_item_custody_balance(
                farm=self.farm,
                supervisor=self.supervisor,
                item=self.item,
            ),
            Decimal("5.000"),
        )

        transfer = CustodyTransferService.return_transfer(
            transfer=transfer,
            actor=self.actor,
            qty="2",
        )
        self.assertEqual(transfer.status, transfer.STATUS_PARTIALLY_CONSUMED)
        self.assertEqual(transfer.returned_qty, Decimal("2.000"))
        self.assertEqual(
            CustodyTransferService.get_item_custody_balance(
                farm=self.farm,
                supervisor=self.supervisor,
                item=self.item,
            ),
            Decimal("3.000"),
        )

        source_inventory = ItemInventory.objects.get(
            farm=self.farm,
            location=self.source_location,
            item=self.item,
        )
        self.assertEqual(source_inventory.qty, Decimal("7.000"))

    def test_issue_blocks_new_transfer_while_balance_is_open(self):
        transfer = CustodyTransferService.issue_transfer(
            farm=self.farm,
            supervisor=self.supervisor,
            item=self.item,
            source_location=self.source_location,
            qty="5",
            actor=self.actor,
            idempotency_key="custody-issue-2",
        )
        CustodyTransferService.accept_transfer(transfer=transfer, actor=self.actor)

        with self.assertRaises(ValidationError):
            CustodyTransferService.issue_transfer(
                farm=self.farm,
                supervisor=self.supervisor,
                item=self.item,
                source_location=self.source_location,
                qty="6",
                actor=self.actor,
                idempotency_key="custody-issue-3",
            )

    def test_top_up_only_issues_net_delta_when_override_is_allowed(self):
        transfer = CustodyTransferService.issue_transfer(
            farm=self.farm,
            supervisor=self.supervisor,
            item=self.item,
            source_location=self.source_location,
            qty="5",
            actor=self.actor,
            idempotency_key="custody-issue-4",
        )
        CustodyTransferService.accept_transfer(transfer=transfer, actor=self.actor)

        top_up = CustodyTransferService.issue_transfer(
            farm=self.farm,
            supervisor=self.supervisor,
            item=self.item,
            source_location=self.source_location,
            qty="8",
            actor=self.actor,
            allow_top_up=True,
            idempotency_key="custody-issue-5",
        )

        self.assertEqual(top_up.issued_qty, Decimal("3.000"))
        warehouse_inventory = ItemInventory.objects.get(
            farm=self.farm,
            location=self.source_location,
            item=self.item,
        )
        self.assertEqual(warehouse_inventory.qty, Decimal("2.000"))
