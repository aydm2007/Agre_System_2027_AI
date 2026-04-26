from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from rest_framework.test import APIClient

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models import (
    Activity,
    Crop,
    DailyLog,
    Farm,
    Location,
    Supervisor,
    SyncConflictDLQ,
    SyncRecord,
    Task,
)
from smart_agri.core.services.custody_transfer_service import CustodyTransferService
from smart_agri.inventory.models import Item, ItemInventory


class OfflineDailyLogReplayTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user("offline-manager", password="pass", is_staff=True)
        manager_group, _ = Group.objects.get_or_create(name="Manager")
        self.user.groups.add(manager_group)
        self.client.force_authenticate(self.user)

        self.farm = Farm.objects.create(name="Offline Farm", slug="offline-farm", region="North")
        FarmMembership.objects.create(user=self.user, farm=self.farm, role="Manager")
        self.supervisor = Supervisor.objects.create(farm=self.farm, name="Ahmed", code="SUP-3")
        self.location = Location.objects.create(farm=self.farm, name="Block 1", code="BLOCK-1", type="Field")
        self.warehouse = Location.objects.create(farm=self.farm, name="Warehouse", code="WH-1", type="Warehouse")
        self.crop = Crop.objects.create(name="Replay Crop", mode="Open")
        self.task = Task.objects.create(crop=self.crop, stage="Care", name="Spraying", requires_tree_count=False)
        self.item = Item.objects.create(name="Replay Urea", group="fertilizer", uom="kg", unit_price=Decimal("10.000"))
        ItemInventory.objects.create(
            farm=self.farm,
            location=self.warehouse,
            item=self.item,
            qty=Decimal("12.000"),
            uom="kg",
        )
        accepted = CustodyTransferService.issue_transfer(
            farm=self.farm,
            supervisor=self.supervisor,
            item=self.item,
            source_location=self.warehouse,
            qty="5",
            actor=self.user,
            idempotency_key="offline-issue-1",
        )
        self.transfer = CustodyTransferService.accept_transfer(transfer=accepted, actor=self.user)
        self.url = "/api/v1/offline/daily-log-replay/atomic/"

    def test_atomic_replay_accepts_frontend_payload_shape_and_is_idempotent(self):
        payload = {
            "uuid": "3b8b4b34-310a-4b2d-8165-08d4c4e74a11",
            "idempotency_key": "3b8b4b34-310a-4b2d-8165-08d4c4e74a11",
            "farm_id": self.farm.id,
            "supervisor_id": self.supervisor.id,
            "client_seq": 1,
            "device_id": "tablet-1",
            "device_timestamp": "2026-04-08T10:00:00Z",
            "log": {
                "log_date": "2026-04-08",
                "notes": "field note",
            },
            "activity": {
                "task": self.task.id,
                "locations": [self.location.id],
                "items_payload": [
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
        }

        response = self.client.post(
            self.url,
            payload,
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="3b8b4b34-310a-4b2d-8165-08d4c4e74a11",
        )
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body["status"], "synced")

        daily_log = DailyLog.objects.get(pk=body["log_id"])
        self.assertEqual(daily_log.supervisor_id, self.supervisor.id)
        self.assertEqual(
            CustodyTransferService.get_item_custody_balance(
                farm=self.farm,
                supervisor=self.supervisor,
                item=self.item,
            ),
            Decimal("2.000"),
        )
        self.assertEqual(
            SyncRecord.objects.filter(reference="offline-log-1", status=SyncRecord.STATUS_SUCCESS).count(),
            0,
        )
        self.assertEqual(
            SyncRecord.objects.filter(
                reference="3b8b4b34-310a-4b2d-8165-08d4c4e74a11",
                status=SyncRecord.STATUS_SUCCESS,
            ).count(),
            1,
        )

        replay = self.client.post(
            self.url,
            payload,
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="3b8b4b34-310a-4b2d-8165-08d4c4e74a11",
        )
        self.assertIn(replay.status_code, (200, 201), replay.content)
        self.assertEqual(replay.json()["activity_id"], body["activity_id"])

    def test_out_of_order_client_sequence_enters_dlq(self):
        response = self.client.post(
            self.url,
            {
                "uuid": "offline-log-2",
                "idempotency_key": "79b8f3af-c6df-44d2-9fe0-efcb88653ed3",
                "farm_id": self.farm.id,
                "supervisor_id": self.supervisor.id,
                "client_seq": 2,
                "device_id": "tablet-2",
                "device_timestamp": "2026-04-08T11:00:00Z",
                "log": {"log_date": "2026-04-08"},
                "activity": {"task": self.task.id, "locations": [self.location.id]},
            },
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="79b8f3af-c6df-44d2-9fe0-efcb88653ed3",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(SyncConflictDLQ.objects.count(), 1)
        conflict = SyncConflictDLQ.objects.get()
        self.assertEqual(conflict.conflict_type, "STALE_VERSION")
        self.assertIn("Expected next seq 1", conflict.conflict_reason)

    def test_multiple_same_day_replays_append_multiple_activities_without_overwrite(self):
        first = {
            "uuid": "11111111-1111-4111-8111-111111111111",
            "draft_uuid": "draft-a",
            "idempotency_key": "11111111-1111-4111-8111-111111111111",
            "farm_id": self.farm.id,
            "supervisor_id": self.supervisor.id,
            "client_seq": 1,
            "device_id": "tablet-3",
            "device_timestamp": "2026-04-08T09:00:00Z",
            "lookup_snapshot_version": "farm:fresh|crop:fresh",
            "task_contract_snapshot": {"enabledCards": {"materials": True, "harvest": False}},
            "log": {"log_date": "2026-04-08", "notes": "first"},
            "activity": {"task": self.task.id, "locations": [self.location.id]},
        }
        second = {
            "uuid": "22222222-2222-4222-8222-222222222222",
            "draft_uuid": "draft-b",
            "idempotency_key": "22222222-2222-4222-8222-222222222222",
            "farm_id": self.farm.id,
            "supervisor_id": self.supervisor.id,
            "client_seq": 2,
            "device_id": "tablet-3",
            "device_timestamp": "2026-04-08T10:30:00Z",
            "lookup_snapshot_version": "farm:stale|crop:fresh",
            "task_contract_snapshot": {"enabledCards": {"materials": False, "harvest": True}},
            "log": {"log_date": "2026-04-08", "notes": "second"},
            "activity": {"task": self.task.id, "locations": [self.location.id]},
        }

        first_response = self.client.post(
            self.url,
            first,
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="11111111-1111-4111-8111-111111111111",
        )
        second_response = self.client.post(
            self.url,
            second,
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="22222222-2222-4222-8222-222222222222",
        )

        self.assertEqual(first_response.status_code, 201, first_response.content)
        self.assertEqual(second_response.status_code, 201, second_response.content)

        daily_log = DailyLog.objects.get(farm=self.farm, supervisor=self.supervisor, log_date="2026-04-08")
        self.assertEqual(Activity.objects.filter(log=daily_log).count(), 2)
        self.assertEqual(
            SyncRecord.objects.filter(reference="11111111-1111-4111-8111-111111111111", status=SyncRecord.STATUS_SUCCESS).count(),
            1,
        )
        self.assertEqual(
            SyncRecord.objects.filter(reference="22222222-2222-4222-8222-222222222222", status=SyncRecord.STATUS_SUCCESS).count(),
            1,
        )
        second_record = SyncRecord.objects.get(reference="22222222-2222-4222-8222-222222222222")
        self.assertEqual(second_record.payload["draft_uuid"], "draft-b")
        self.assertEqual(second_record.payload["lookup_snapshot_version"], "farm:stale|crop:fresh")

    def test_mango_all_activity_replay_creates_visible_daily_log(self):
        mango = Crop.objects.create(name="مانجو", mode="Open", is_perennial=True)
        mango_task = Task.objects.create(
            crop=mango,
            stage="تشغيل",
            name="نشاط الكل",
            requires_tree_count=False,
        )
        payload = {
            "uuid": "33333333-3333-4333-8333-333333333333",
            "draft_uuid": "mango-draft",
            "idempotency_key": "33333333-3333-4333-8333-333333333333",
            "farm_id": self.farm.id,
            "supervisor_id": self.supervisor.id,
            "client_seq": 1,
            "device_id": "mango-tablet",
            "device_timestamp": "2026-04-25T08:00:00Z",
            "log": {"log_date": "2026-04-25", "notes": "mango local test"},
            "activity": {
                "crop": mango.id,
                "task": mango_task.id,
                "locations": [self.location.id],
                "planted_area": "",
                "cost_materials": "10.1234567",
                "cost_total": "11.9999999",
            },
        }

        response = self.client.post(
            self.url,
            payload,
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="33333333-3333-4333-8333-333333333333",
        )

        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertTrue(DailyLog.objects.filter(pk=body["log_id"], farm=self.farm).exists())
        self.assertTrue(Activity.objects.filter(pk=body["activity_id"], crop=mango, task=mango_task).exists())
        self.assertTrue(
            SyncRecord.objects.filter(
                reference="33333333-3333-4333-8333-333333333333",
                status=SyncRecord.STATUS_SUCCESS,
            ).exists()
        )

        history = self.client.get("/api/v1/daily-logs/", {"farm": self.farm.id})
        self.assertEqual(history.status_code, 200, history.content)
        rows = history.json().get("results", history.json())
        self.assertTrue(any(row["id"] == body["log_id"] for row in rows))
