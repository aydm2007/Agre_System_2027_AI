from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from rest_framework.test import APIClient

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models import (
    Activity,
    Asset,
    Crop,
    CropVariety,
    DailyLog,
    Farm,
    Location,
    Supervisor,
    SyncConflictDLQ,
    OfflineSyncQuarantine,
    SyncRecord,
    Task,
    TreeServiceCoverage,
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
        self.variety = CropVariety.objects.create(crop=self.crop, name="Replay Variety")
        self.task = Task.objects.create(crop=self.crop, stage="Care", name="Spraying", requires_tree_count=False)
        self.asset = Asset.objects.create(
            farm=self.farm,
            name="Offline Tractor",
            code="OFF-TRACTOR-1",
            category="Machinery",
        )
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
                "variety_id": self.variety.id,
                "tree_count_delta": 1,
                "activity_tree_count": 1,
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
                "service_counts_payload": [
                    {
                        "location_id": self.location.id,
                        "variety_id": self.variety.id,
                        "service_count": 1,
                        "service_type": TreeServiceCoverage.GENERAL,
                        "service_scope": "location",
                        "distribution_mode": "equal",
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
        coverage = TreeServiceCoverage.objects.get(activity_id=body["activity_id"])
        self.assertEqual(coverage.distribution_mode, TreeServiceCoverage.DISTRIBUTION_UNIFORM)
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

        mismatch_payload = {
            **payload,
            "log": {
                **payload["log"],
                "notes": "changed after first submission",
            },
        }
        mismatch = self.client.post(
            self.url,
            mismatch_payload,
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="3b8b4b34-310a-4b2d-8165-08d4c4e74a11",
        )
        self.assertEqual(mismatch.status_code, 409, mismatch.content)
        self.assertEqual(mismatch.json()["code"], "IDEMPOTENCY_MISMATCH")

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

    def test_legacy_asset_alias_and_rotated_non_uuid_key_replay(self):
        payload = {
            "uuid": "44444444-4444-4444-8444-444444444444",
            "draft_uuid": "legacy-asset-draft",
            "idempotency_key": "55555555-5555-4555-8555-555555555555",
            "farm_id": self.farm.id,
            "supervisor_id": self.supervisor.id,
            "client_seq": 1,
            "device_id": "legacy-asset-tablet",
            "device_timestamp": "2026-04-29T13:12:08Z",
            "logPayload": {"farm": self.farm.id, "log_date": "2026-04-29", "notes": ""},
            "activityPayload": {
                "task": str(self.task.id),
                "locations": [self.location.id],
                "asset": str(self.asset.id),
                "asset_id": str(self.asset.id),
                "machine_hours": "2",
                "tree_loss_reason": "",
                "tree_loss_reason_id": "",
                "tree_count_delta": "0",
            },
        }

        response = self.client.post(
            self.url,
            payload,
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="55555555-5555-4555-8555-555555555555",
        )

        self.assertEqual(response.status_code, 201, response.content)
        activity = Activity.objects.get(pk=response.json()["activity_id"])
        self.assertEqual(activity.asset_id, self.asset.id)
        self.assertIsNone(activity.tree_loss_reason_id)
        self.assertEqual(str(activity.idempotency_key), payload["idempotency_key"])

    def test_replay_reuses_canonical_daily_log_when_duplicate_same_day_logs_exist(self):
        keeper = DailyLog.objects.create(
            farm=self.farm,
            supervisor=self.supervisor,
            log_date="2026-04-29",
            status=DailyLog.STATUS_DRAFT,
            notes="keeper",
            created_by=self.user,
            updated_by=self.user,
        )
        duplicate = DailyLog.objects.create(
            farm=self.farm,
            supervisor=self.supervisor,
            log_date="2026-04-29",
            status=DailyLog.STATUS_DRAFT,
            notes="duplicate",
            created_by=self.user,
            updated_by=self.user,
        )
        payload = {
            "uuid": "66666666-6666-4666-8666-666666666666",
            "draft_uuid": "duplicate-draft",
            "idempotency_key": "66666666-6666-4666-8666-666666666666",
            "farm_id": self.farm.id,
            "supervisor_id": self.supervisor.id,
            "client_seq": 1,
            "device_id": "duplicate-tablet",
            "device_timestamp": "2026-04-29T14:35:12Z",
            "logPayload": {"farm": self.farm.id, "log_date": "2026-04-29", "notes": "replayed note"},
            "activityPayload": {
                "task": self.task.id,
                "locations": [self.location.id],
                "asset_id": self.asset.id,
            },
        }

        response = self.client.post(
            self.url,
            payload,
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="66666666-6666-4666-8666-666666666666",
        )

        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body["log_id"], keeper.id)
        self.assertTrue(Activity.objects.filter(pk=body["activity_id"], log_id=keeper.id).exists())
        duplicate.refresh_from_db()
        self.assertEqual(duplicate.notes, "duplicate")

    def test_successful_replay_marks_related_pending_dlq_as_replayed(self):
        SyncConflictDLQ.objects.create(
            farm=self.farm,
            actor=self.user,
            conflict_type="VALIDATION_FAILURE",
            conflict_reason="legacy pending failure",
            endpoint=self.url,
            http_method="POST",
            request_payload={
                "uuid": "77777777-7777-4777-8777-777777777777",
                "payload_uuid": "77777777-7777-4777-8777-777777777777",
                "draft_uuid": "draft-to-resolve",
            },
            idempotency_key="legacy-dlq-key",
            status="PENDING",
        )
        payload = {
            "uuid": "77777777-7777-4777-8777-777777777777",
            "draft_uuid": "draft-to-resolve",
            "idempotency_key": "77777777-7777-4777-8777-777777777777",
            "farm_id": self.farm.id,
            "supervisor_id": self.supervisor.id,
            "client_seq": 1,
            "device_id": "resolve-dlq-tablet",
            "device_timestamp": "2026-04-29T18:00:00Z",
            "logPayload": {"farm": self.farm.id, "log_date": "2026-04-29", "notes": ""},
            "activityPayload": {"task": self.task.id, "locations": [self.location.id]},
        }

        response = self.client.post(
            self.url,
            payload,
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="77777777-7777-4777-8777-777777777777",
        )

        self.assertEqual(response.status_code, 201, response.content)
        dlq = SyncConflictDLQ.objects.get(idempotency_key="legacy-dlq-key")
        self.assertEqual(dlq.status, "REPLAYED")
        self.assertEqual(dlq.resolved_by_id, self.user.id)
