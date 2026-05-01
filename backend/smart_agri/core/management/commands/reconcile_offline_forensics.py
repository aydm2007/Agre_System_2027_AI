from __future__ import annotations

from collections import defaultdict

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from smart_agri.core.models.log import SyncRecord
from smart_agri.core.models.sync_conflict import OfflineSyncQuarantine, SyncConflictDLQ
from smart_agri.core.services.quarantine_service import ModeSwitchQuarantineService


class Command(BaseCommand):
    help = "Reconcile legacy offline DLQ/quarantine rows after replay fixes in trial environments."

    def add_arguments(self, parser):
        parser.add_argument("--farm-id", type=int, required=True, help="Target farm id.")
        parser.add_argument(
            "--resolver-username",
            type=str,
            default="",
            help="Resolver username for quarantine approvals. Defaults to the first superuser.",
        )
        parser.add_argument("--dry-run", action="store_true", help="Report only; do not persist changes.")
        parser.add_argument(
            "--close-legacy-pending",
            action="store_true",
            help="Resolve remaining PENDING STALE_VERSION/VALIDATION_FAILURE rows as legacy trial artifacts.",
        )
        parser.add_argument(
            "--approve-mode-switch-quarantines",
            action="store_true",
            help="Approve pending MODE_SWITCH_QUARANTINE rows and remove quarantine note from linked logs.",
        )

    def handle(self, *args, **options):
        farm_id = options["farm_id"]
        dry_run = options["dry_run"]
        close_legacy_pending = options["close_legacy_pending"]
        approve_mode_switch = options["approve_mode_switch_quarantines"]

        resolver = self._resolve_resolver(options.get("resolver_username") or "")
        if approve_mode_switch and resolver is None:
            raise CommandError("No resolver user available for quarantine approval.")

        summary = {
            "replayed": 0,
            "resolved_duplicates": 0,
            "resolved_legacy_pending": 0,
            "approved_mode_switch_quarantines": 0,
            "remaining_pending_dlq": 0,
            "remaining_pending_quarantines": 0,
        }

        with transaction.atomic():
            summary["replayed"] = self._mark_replayed_from_success(farm_id=farm_id, dry_run=dry_run)
            summary["resolved_duplicates"] = self._resolve_duplicate_pending(farm_id=farm_id, dry_run=dry_run)
            if close_legacy_pending:
                summary["resolved_legacy_pending"] = self._resolve_legacy_pending(farm_id=farm_id, dry_run=dry_run)
            if approve_mode_switch:
                summary["approved_mode_switch_quarantines"] = self._approve_mode_switch_quarantines(
                    farm_id=farm_id,
                    resolver=resolver,
                    dry_run=dry_run,
                )
            if dry_run:
                transaction.set_rollback(True)

        summary["remaining_pending_dlq"] = SyncConflictDLQ.objects.filter(
            farm_id=farm_id,
            deleted_at__isnull=True,
            status="PENDING",
        ).exclude(idempotency_key__startswith="demo-").exclude(request_payload__has_key="demo_fixture").count()
        summary["remaining_pending_quarantines"] = OfflineSyncQuarantine.objects.filter(
            farm_id=farm_id,
            deleted_at__isnull=True,
            status="PENDING_REVIEW",
        ).exclude(idempotency_key__startswith="demo-").exclude(original_payload__has_key="demo_fixture").count()

        for key, value in summary.items():
            self.stdout.write(f"{key}={value}")

    def _resolve_resolver(self, username: str):
        user_model = get_user_model()
        if username:
            resolver = user_model.objects.filter(username=username).first()
            if resolver is None:
                raise CommandError(f"Resolver user '{username}' was not found.")
            return resolver
        return user_model.objects.filter(is_superuser=True).order_by("id").first()

    @staticmethod
    def _extract_identity(payload):
        if not isinstance(payload, dict):
            return None, None
        return payload.get("payload_uuid") or payload.get("uuid"), payload.get("draft_uuid")

    def _mark_replayed_from_success(self, *, farm_id: int, dry_run: bool) -> int:
        success_refs = set(
            SyncRecord.objects.filter(farm_id=farm_id, status=SyncRecord.STATUS_SUCCESS)
            .values_list("user_id", "reference")
        )
        now = timezone.now()
        updated = 0
        rows = SyncConflictDLQ.objects.filter(
            farm_id=farm_id,
            deleted_at__isnull=True,
            status="PENDING",
        ).exclude(idempotency_key__startswith="demo-").exclude(request_payload__has_key="demo_fixture")
        for row in rows:
            payload_uuid, draft_uuid = self._extract_identity(row.request_payload)
            if not payload_uuid or (row.actor_id, payload_uuid) not in success_refs:
                continue
            updated += 1
            if dry_run:
                continue
            row.status = "REPLAYED"
            row.resolved_by_id = row.actor_id
            row.resolved_at = now
            row.resolution_notes = (
                f"Bulk reconciled after successful replay for payload_uuid={payload_uuid} "
                f"draft_uuid={draft_uuid or '-'}."
            )
            row.save(update_fields=["status", "resolved_by", "resolved_at", "resolution_notes", "updated_at"])
        return updated

    def _resolve_duplicate_pending(self, *, farm_id: int, dry_run: bool) -> int:
        groups = defaultdict(list)
        rows = SyncConflictDLQ.objects.filter(
            farm_id=farm_id,
            deleted_at__isnull=True,
            status="PENDING",
        ).exclude(idempotency_key__startswith="demo-").exclude(request_payload__has_key="demo_fixture").order_by("id")
        for row in rows:
            payload_uuid, draft_uuid = self._extract_identity(row.request_payload)
            identity = payload_uuid or (f"draft:{draft_uuid}" if draft_uuid else f"idemp:{row.idempotency_key or row.id}")
            groups[(row.actor_id, row.endpoint, row.conflict_type, identity)].append(row)

        now = timezone.now()
        updated = 0
        for bucket in groups.values():
            if len(bucket) <= 1:
                continue
            keeper = bucket[-1]
            for row in bucket[:-1]:
                updated += 1
                if dry_run:
                    continue
                row.status = "RESOLVED"
                row.resolved_by_id = row.actor_id
                row.resolved_at = now
                row.resolution_notes = f"Superseded duplicate; keeper DLQ #{keeper.id}."
                row.save(update_fields=["status", "resolved_by", "resolved_at", "resolution_notes", "updated_at"])
        return updated

    def _resolve_legacy_pending(self, *, farm_id: int, dry_run: bool) -> int:
        rows = SyncConflictDLQ.objects.filter(
            farm_id=farm_id,
            deleted_at__isnull=True,
            status="PENDING",
            conflict_type__in=["STALE_VERSION", "VALIDATION_FAILURE"],
        ).exclude(idempotency_key__startswith="demo-").exclude(request_payload__has_key="demo_fixture")
        now = timezone.now()
        updated = rows.count()
        if dry_run:
            return updated
        for row in rows:
            row.status = "RESOLVED"
            row.resolved_by_id = row.actor_id
            row.resolved_at = now
            row.resolution_notes = (
                "Legacy offline replay artifact closed after replay hardening and queue normalization."
            )
            row.save(update_fields=["status", "resolved_by", "resolved_at", "resolution_notes", "updated_at"])
        return updated

    def _approve_mode_switch_quarantines(self, *, farm_id: int, resolver, dry_run: bool) -> int:
        rows = list(
            OfflineSyncQuarantine.objects.filter(
                farm_id=farm_id,
                deleted_at__isnull=True,
                status="PENDING_REVIEW",
                variance_type="MODE_SWITCH_QUARANTINE",
            ).exclude(idempotency_key__startswith="demo-").exclude(original_payload__has_key="demo_fixture")
        )
        if dry_run:
            return len(rows)
        approved = 0
        for row in rows:
            ModeSwitchQuarantineService.resolve_quarantine(
                quarantine_id=row.id,
                action="approve",
                manager=resolver,
                reason="Trial-environment offline reconciliation after replay hardening.",
            )
            approved += 1
        return approved
