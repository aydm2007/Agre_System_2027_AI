from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from rest_framework.test import APIClient

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models import Crop, CropPlan, Farm, Location, Supervisor, SyncRecord
from smart_agri.core.models.custody import CustodyTransfer
from smart_agri.inventory.models import Item, ItemInventory, Unit


class OfflineOperationalReplayTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user("offline-ops-manager", password="pass", is_staff=True)
        manager_group, _ = Group.objects.get_or_create(name="Manager")
        self.user.groups.add(manager_group)
        self.client.force_authenticate(self.user)

        self.farm = Farm.objects.create(name="Offline Ops Farm", slug="offline-ops-farm", region="North")
        FarmMembership.objects.create(user=self.user, farm=self.farm, role="Manager")
        self.supervisor = Supervisor.objects.create(farm=self.farm, name="Saeed", code="SUP-OPS")
        self.warehouse = Location.objects.create(farm=self.farm, name="Warehouse", code="WH-OPS", type="Warehouse")
        self.crop = Crop.objects.create(name="Replay Harvest Crop", mode="Open")
        self.plan = CropPlan.objects.create(
            farm=self.farm,
            crop=self.crop,
            season="2026",
            area=Decimal("5.000"),
            status="active",
            name="Offline Harvest Plan",
        )
        self.unit = Unit.objects.create(name="Kilogram", symbol="kg", code="KG")
        self.item = Item.objects.create(
            name="Replay Product",
            group="Harvested Product",
            uom="kg",
            unit_price=Decimal("12.000"),
        )
        ItemInventory.objects.create(
            farm=self.farm,
            location=self.warehouse,
            item=self.item,
            qty=Decimal("50.000"),
            uom="kg",
        )

    def test_offline_harvest_replay_accepts_modal_payload_and_is_idempotent(self):
        payload = {
            "uuid": "harvest-offline-1",
            "payload_uuid": "harvest-offline-1",
            "idempotency_key": "harvest-idemp-1",
            "farm_id": self.farm.id,
            "client_seq": 1,
            "device_id": "tablet-harvest-1",
            "device_timestamp": "2026-04-18T10:00:00Z",
            "harvest": {
                "crop_plan": self.plan.id,
                "date": "2026-04-18",
                "product_item": self.item.id,
                "qty": "25.500",
                "unit": self.unit.id,
                "notes": "offline harvest",
            },
        }
        response = self.client.post(
            "/api/v1/offline/harvest-replay/atomic/",
            payload,
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="harvest-idemp-1",
        )
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body["status"], "synced")
        self.assertTrue(
            SyncRecord.objects.filter(
                reference="harvest-offline-1",
                category="harvest",
                status=SyncRecord.STATUS_SUCCESS,
            ).exists()
        )

        replay = self.client.post(
            "/api/v1/offline/harvest-replay/atomic/",
            payload,
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="harvest-idemp-1",
        )
        self.assertIn(replay.status_code, (200, 201), replay.content)
        self.assertEqual(replay.json()["harvest_id"], body["harvest_id"])

    def test_offline_custody_replay_issues_transfer_and_records_sync(self):
        payload = {
            "uuid": "custody-offline-1",
            "payload_uuid": "custody-offline-1",
            "idempotency_key": "custody-idemp-1",
            "farm_id": self.farm.id,
            "client_seq": 1,
            "device_id": "tablet-custody-1",
            "device_timestamp": "2026-04-18T11:00:00Z",
            "action_name": "issue",
            "payload": {
                "farm_id": self.farm.id,
                "supervisor_id": self.supervisor.id,
                "item_id": self.item.id,
                "from_location_id": self.warehouse.id,
                "qty": "5.000",
                "note": "offline custody issue",
            },
        }
        response = self.client.post(
            "/api/v1/offline/custody-replay/atomic/",
            payload,
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="custody-idemp-1",
        )
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body["status"], "synced")
        self.assertTrue(
            CustodyTransfer.objects.filter(pk=body["transfer_id"], farm=self.farm).exists()
        )
        self.assertTrue(
            SyncRecord.objects.filter(
                reference="custody-offline-1",
                category="custody",
                status=SyncRecord.STATUS_SUCCESS,
            ).exists()
        )

    def test_manager_can_list_dlq_and_quarantine_surfaces(self):
        SyncRecord.objects.create(
            user=self.user,
            farm=self.farm,
            category="harvest",
            reference="surface-sync-1",
            status=SyncRecord.STATUS_SUCCESS,
        )
        from smart_agri.core.models.sync_conflict import OfflineSyncQuarantine, SyncConflictDLQ

        SyncConflictDLQ.objects.create(
            farm=self.farm,
            actor=self.user,
            conflict_type="VALIDATION_FAILURE",
            conflict_reason="offline failure",
            endpoint="/api/v1/offline/harvest-replay/atomic/",
            http_method="POST",
            request_payload={"uuid": "failed-1"},
            idempotency_key="failed-idemp-1",
        )
        OfflineSyncQuarantine.objects.create(
            farm=self.farm,
            submitted_by=self.user,
            variance_type="LATE_CRITICAL_VARIANCE",
            device_timestamp="2026-04-17T10:00:00Z",
            original_payload={"uuid": "quarantine-1"},
            idempotency_key="quarantine-idemp-1",
        )

        sync_response = self.client.get("/api/v1/sync-records/", {"category": "harvest"})
        dlq_response = self.client.get("/api/v1/sync-conflict-dlq/")
        quarantine_response = self.client.get("/api/v1/offline-sync-quarantines/")

        self.assertEqual(sync_response.status_code, 200)
        self.assertEqual(dlq_response.status_code, 200)
        self.assertEqual(quarantine_response.status_code, 200)
        self.assertGreaterEqual(len(sync_response.json()), 1)
        self.assertGreaterEqual(len(dlq_response.json()), 1)
        self.assertGreaterEqual(len(quarantine_response.json()), 1)
