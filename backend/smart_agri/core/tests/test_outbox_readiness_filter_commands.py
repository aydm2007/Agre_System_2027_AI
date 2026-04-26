import os
from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from smart_agri.core.models import IntegrationOutboxEvent
from smart_agri.integration_hub.event_contracts import InventoryChanged
from smart_agri.integration_hub.persistence import persist_event, persistent_outbox_snapshot
from smart_agri.integration_hub.registry import reset_registry


class OutboxReadinessFilterCommandTests(TestCase):
    def setUp(self):
        self.original_mode = os.environ.get("INTEGRATION_HUB_PUBLISHER")
        os.environ["INTEGRATION_HUB_PUBLISHER"] = "readiness_composite"
        reset_registry()

    def tearDown(self):
        if self.original_mode is None:
            os.environ.pop("INTEGRATION_HUB_PUBLISHER", None)
        else:
            os.environ["INTEGRATION_HUB_PUBLISHER"] = self.original_mode
        reset_registry()

    def _event(self, *, event_id: str, flagged: bool, destination: str = "readiness/success") -> IntegrationOutboxEvent:
        metadata = {"seed_runtime_governance": True} if flagged else {}
        return persist_event(
            InventoryChanged(
                aggregate_id=f"aggregate-{event_id}",
                sku=f"SKU-{event_id}",
                delta_quantity=1,
                event_id=event_id,
                metadata=metadata,
            ),
            destination=destination,
        )

    def test_dispatch_outbox_metadata_flag_only_processes_seeded_rows(self):
        flagged = self._event(event_id="dispatch-flagged", flagged=True)
        unflagged = self._event(event_id="dispatch-unflagged", flagged=False)

        stdout = StringIO()
        call_command("dispatch_outbox", "--batch-size", "10", "--metadata-flag", "seed_runtime_governance", stdout=stdout)

        flagged.refresh_from_db()
        unflagged.refresh_from_db()

        self.assertEqual(flagged.status, IntegrationOutboxEvent.Status.DISPATCHED)
        self.assertEqual(unflagged.status, IntegrationOutboxEvent.Status.PENDING)
        self.assertEqual(persistent_outbox_snapshot(metadata_flag="seed_runtime_governance")["total"], 1)

    def test_retry_dead_letters_metadata_flag_only_requeues_seeded_rows(self):
        flagged = self._event(event_id="retry-flagged", flagged=True)
        unflagged = self._event(event_id="retry-unflagged", flagged=False)
        IntegrationOutboxEvent.objects.filter(pk=flagged.pk).update(
            status=IntegrationOutboxEvent.Status.DEAD_LETTER,
            attempts=flagged.max_attempts,
            last_error="flagged_dead_letter",
        )
        IntegrationOutboxEvent.objects.filter(pk=unflagged.pk).update(
            status=IntegrationOutboxEvent.Status.DEAD_LETTER,
            attempts=unflagged.max_attempts,
            last_error="unflagged_dead_letter",
        )

        stdout = StringIO()
        call_command("retry_dead_letters", "--limit", "10", "--metadata-flag", "seed_runtime_governance", stdout=stdout)

        flagged.refresh_from_db()
        unflagged.refresh_from_db()

        self.assertEqual(flagged.status, IntegrationOutboxEvent.Status.FAILED)
        self.assertEqual(unflagged.status, IntegrationOutboxEvent.Status.DEAD_LETTER)
        self.assertTrue(flagged.last_error.startswith("[manual-retry]"))

    def test_purge_dispatched_outbox_metadata_flag_only_deletes_seeded_rows(self):
        flagged = self._event(event_id="purge-flagged", flagged=True)
        unflagged = self._event(event_id="purge-unflagged", flagged=False)
        old_time = timezone.now() - timedelta(hours=2)
        IntegrationOutboxEvent.objects.filter(pk=flagged.pk).update(
            status=IntegrationOutboxEvent.Status.DISPATCHED,
            dispatched_at=old_time,
            available_at=old_time,
        )
        IntegrationOutboxEvent.objects.filter(pk=unflagged.pk).update(
            status=IntegrationOutboxEvent.Status.DISPATCHED,
            dispatched_at=old_time,
            available_at=old_time,
        )

        stdout = StringIO()
        call_command("purge_dispatched_outbox", "--older-than-hours", "1", "--metadata-flag", "seed_runtime_governance", stdout=stdout)

        self.assertFalse(IntegrationOutboxEvent.objects.filter(pk=flagged.pk).exists())
        self.assertTrue(IntegrationOutboxEvent.objects.filter(pk=unflagged.pk).exists())
