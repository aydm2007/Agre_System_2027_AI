from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from smart_agri.core.api.permissions import user_has_any_farm_role, user_has_sector_finance_authority
from smart_agri.core.models import (
    Attachment,
    AttachmentLifecycleEvent,
    IntegrationOutboxEvent,
    OfflineSyncQuarantine,
    OpsAlertReceipt,
    SyncConflictDLQ,
)
from smart_agri.core.services.ops_health_service import OpsHealthService
from smart_agri.finance.services.approval_service import ApprovalGovernanceService


logger = logging.getLogger(__name__)


class OpsAlertService:
    OPERATOR_ROLES = {
        "رئيس حسابات القطاع",
        "المدير المالي لقطاع المزارع",
        "مدير القطاع",
        "مدير النظام",
    }
    SNOOZE_PRESETS_HOURS = {1, 4, 24}
    SEVERITY_ORDER = {"critical": 0, "attention": 1}

    @classmethod
    def _has_operator_access(cls, *, user) -> bool:
        if not getattr(user, "is_authenticated", False):
            return False
        if getattr(user, "is_superuser", False):
            return True
        if user_has_sector_finance_authority(user):
            return True
        return user_has_any_farm_role(user, cls.OPERATOR_ROLES)

    @classmethod
    def _ensure_operator(cls, *, user) -> None:
        if not cls._has_operator_access(user=user):
            raise PermissionDenied("Operator observability is restricted to sector/system operators.")

    @staticmethod
    def _fingerprint(kind: str, scope_type: str, scope_id: str, canonical_reason: str) -> str:
        return f"{kind}:{scope_type}:{scope_id}:{canonical_reason}"

    @staticmethod
    def _severity(raw: str | None) -> str:
        return "critical" if str(raw or "").lower() == "critical" else "attention"

    @staticmethod
    def _runbook_key(kind: str) -> str:
        return {
            "approval_runtime_attention": "approval_runtime_runbook",
            "attachment_runtime_attention": "attachment_runtime_runbook",
            "outbox_dead_letter_attention": "outbox_dead_letter_runbook",
            "release_health_warning": "release_health_runbook",
            "offline_sync_attention": "offline_sync_runbook",
        }.get(kind, "ops_runtime_runbook")

    @staticmethod
    def _deep_link(
        *,
        kind: str,
        farm_id: int | None = None,
        request_id: int | None = None,
        attachment_id: int | None = None,
        event_id: int | str | None = None,
        release_key: str | None = None,
    ) -> str:
        if kind == "approval_runtime_attention":
            params = ["tab=runtime"]
            if farm_id:
                params.append(f"farm={farm_id}")
            if request_id:
                params.append(f"request={request_id}")
            return f"/approvals?{'&'.join(params)}"
        if kind == "attachment_runtime_attention":
            params = ["tab=governance", "governanceTab=ops"]
            if farm_id:
                params.append(f"farm={farm_id}")
            if attachment_id:
                params.append(f"attachment_id={attachment_id}")
            return f"/settings?{'&'.join(params)}"
        if kind == "outbox_dead_letter_attention":
            params = ["tab=governance", "governanceTab=ops"]
            if farm_id:
                params.append(f"farm={farm_id}")
            if event_id:
                params.append(f"event_id={event_id}")
            return f"/settings?{'&'.join(params)}"
        if kind == "offline_sync_attention":
            params = ["tab=offline"]
            if farm_id:
                params.append(f"farm={farm_id}")
            return f"/settings?{'&'.join(params)}"
        params = ["tab=governance", "governanceTab=ops", "section=release"]
        if release_key:
            params.append(f"release_key={release_key}")
        return f"/settings?{'&'.join(params)}"

    @classmethod
    def _make_alert(
        cls,
        *,
        kind: str,
        severity: str,
        farm_id: int | None,
        scope_type: str,
        scope_id: str,
        canonical_reason: str,
        deep_link: str,
        source_snapshot: dict,
        request_id: int | None = None,
        correlation_id: str | None = None,
        title: str = "",
    ) -> dict:
        return {
            "fingerprint": cls._fingerprint(kind, scope_type, scope_id, canonical_reason),
            "kind": kind,
            "severity": severity,
            "farm_id": farm_id,
            "scope_type": scope_type,
            "scope_id": str(scope_id),
            "canonical_reason": canonical_reason,
            "request_id": request_id,
            "correlation_id": correlation_id,
            "deep_link": deep_link,
            "runbook_key": cls._runbook_key(kind),
            "title": title or canonical_reason.replace("_", " "),
            "source_snapshot": source_snapshot,
            "created_at": source_snapshot.get("created_at") or timezone.now().isoformat(),
        }

    @classmethod
    def _approval_alerts(cls, *, farm_id: int | None = None) -> list[dict]:
        alerts = []
        for item in ApprovalGovernanceService.attention_feed().get("items", []):
            if farm_id and item.get("farm_id") not in {farm_id, None}:
                continue
            request_id = item.get("request_id") or (item.get("sample_request_ids") or [None])[0]
            scope_type = "approval_request" if request_id else "approval_lane"
            scope_id = request_id or f"{item.get('farm_id') or 'global'}:{item.get('role') or item.get('kind')}"
            canonical_reason = item.get("attention_bucket") or item.get("kind") or "approval_runtime_attention"
            alerts.append(
                cls._make_alert(
                    kind="approval_runtime_attention",
                    severity=cls._severity(item.get("severity")),
                    farm_id=item.get("farm_id"),
                    scope_type=scope_type,
                    scope_id=str(scope_id),
                    canonical_reason=canonical_reason,
                    deep_link=cls._deep_link(
                        kind="approval_runtime_attention",
                        farm_id=item.get("farm_id"),
                        request_id=request_id,
                    ),
                    source_snapshot={
                        "origin": "approval_attention_feed",
                        "message": item.get("message"),
                        "role": item.get("role"),
                        "role_label": item.get("role_label"),
                        "sample_request_ids": item.get("sample_request_ids", []),
                        "created_at": item.get("created_at"),
                    },
                    request_id=request_id,
                    correlation_id=f"approval-request-{request_id}" if request_id else None,
                    title=item.get("message") or "approval runtime attention",
                )
            )
        return alerts

    @classmethod
    def _attachment_alerts(cls, *, farm_id: int | None = None) -> list[dict]:
        detail = OpsHealthService.attachment_runtime_detail_snapshot(farm_id=farm_id, limit=100)
        grouped = {}
        for row in detail.get("detail_rows", []):
            key = (row.get("farm_id"), row.get("canonical_reason"))
            bucket = grouped.setdefault(
                key,
                {
                    "farm_id": row.get("farm_id"),
                    "farm_name": row.get("farm_name"),
                    "canonical_reason": row.get("canonical_reason") or "attachment_runtime_attention",
                    "count": 0,
                    "sample_attachment_id": row.get("id"),
                    "created_at": row.get("quarantined_at") or row.get("archived_at") or row.get("authoritative_at"),
                },
            )
            bucket["count"] += 1
        return [
            cls._make_alert(
                kind="attachment_runtime_attention",
                severity="critical" if bucket["canonical_reason"] == "attachment_scan_blocked" else "attention",
                farm_id=bucket["farm_id"],
                scope_type="farm",
                scope_id=str(bucket["farm_id"] or "global"),
                canonical_reason=bucket["canonical_reason"],
                deep_link=cls._deep_link(
                    kind="attachment_runtime_attention",
                    farm_id=bucket["farm_id"],
                    attachment_id=bucket["sample_attachment_id"],
                ),
                source_snapshot={
                    "origin": "attachment_runtime_detail",
                    "count": bucket["count"],
                    "farm_name": bucket["farm_name"],
                    "sample_attachment_id": bucket["sample_attachment_id"],
                    "created_at": bucket["created_at"],
                },
                correlation_id=f"attachment-{bucket['sample_attachment_id']}" if bucket["sample_attachment_id"] else None,
                title=f"{bucket['canonical_reason']} ({bucket['count']})",
            )
            for bucket in grouped.values()
        ]

    @classmethod
    def _outbox_alerts(cls, *, farm_id: int | None = None) -> list[dict]:
        detail = OpsHealthService.integration_outbox_detail_snapshot(farm_id=farm_id, limit=100)
        grouped = {}
        for row in detail.get("detail_rows", []):
            key = (row.get("farm_id"), row.get("canonical_reason"))
            bucket = grouped.setdefault(
                key,
                {
                    "farm_id": row.get("farm_id"),
                    "farm_name": row.get("farm_name"),
                    "canonical_reason": row.get("canonical_reason") or "outbox_dead_letter_attention",
                    "count": 0,
                    "sample_event_id": row.get("id"),
                    "correlation_id": row.get("correlation_id"),
                    "created_at": row.get("updated_at") or row.get("available_at"),
                },
            )
            bucket["count"] += 1
        return [
            cls._make_alert(
                kind="outbox_dead_letter_attention",
                severity="critical" if bucket["canonical_reason"] == "dead_letter" else "attention",
                farm_id=bucket["farm_id"],
                scope_type="farm",
                scope_id=str(bucket["farm_id"] or "global"),
                canonical_reason=bucket["canonical_reason"],
                deep_link=cls._deep_link(
                    kind="outbox_dead_letter_attention",
                    farm_id=bucket["farm_id"],
                    event_id=bucket["sample_event_id"],
                ),
                source_snapshot={
                    "origin": "integration_outbox_detail",
                    "count": bucket["count"],
                    "farm_name": bucket["farm_name"],
                    "sample_event_id": bucket["sample_event_id"],
                    "created_at": bucket["created_at"],
                },
                correlation_id=bucket["correlation_id"],
                title=f"{bucket['canonical_reason']} ({bucket['count']})",
            )
            for bucket in grouped.values()
        ]

    @classmethod
    def _release_alerts(cls) -> list[dict]:
        detail = OpsHealthService.release_health_detail_snapshot()
        alerts = []
        for row in detail.get("detail_rows", []):
            stale = bool(row.get("stale"))
            status = str(row.get("status") or "").upper()
            if not stale and status == "PASS":
                continue
            canonical_reason = "stale_or_missing" if stale else f"release_status_{status.lower() or 'unknown'}"
            alerts.append(
                cls._make_alert(
                    kind="release_health_warning",
                    severity="critical" if status not in {"", "PASS"} else "attention",
                    farm_id=None,
                    scope_type="release_check",
                    scope_id=row.get("key") or "release-health",
                    canonical_reason=canonical_reason,
                    deep_link=cls._deep_link(
                        kind="release_health_warning",
                        release_key=row.get("key"),
                    ),
                    source_snapshot={
                        "origin": "release_health_detail",
                        "status": row.get("status"),
                        "stale": stale,
                        "warnings": row.get("warnings", []),
                        "created_at": row.get("generated_at"),
                    },
                    title=f"{row.get('key')}: {canonical_reason}",
                )
            )
        return alerts

    @classmethod
    def offline_ops_snapshot(cls, *, farm_id: int | None = None) -> dict:
        conflict_qs = SyncConflictDLQ.objects.filter(
            deleted_at__isnull=True,
            status="PENDING",
        ).exclude(
            idempotency_key__startswith="demo-",
        ).exclude(
            request_payload__has_key="demo_fixture",
        ).select_related("farm")
        quarantine_qs = OfflineSyncQuarantine.objects.filter(
            deleted_at__isnull=True,
            status="PENDING_REVIEW",
        ).exclude(
            idempotency_key__startswith="demo-",
        ).exclude(
            original_payload__has_key="demo_fixture",
        ).select_related("farm")
        if farm_id:
            conflict_qs = conflict_qs.filter(farm_id=farm_id)
            quarantine_qs = quarantine_qs.filter(farm_id=farm_id)

        by_farm = defaultdict(
            lambda: {
                "farm_id": None,
                "farm_name": "",
                "sync_conflicts": 0,
                "quarantined_payloads": 0,
                "mode_switch_quarantines": 0,
            }
        )
        for row in conflict_qs:
            bucket = by_farm[row.farm_id or 0]
            bucket["farm_id"] = row.farm_id
            bucket["farm_name"] = getattr(row.farm, "name", "")
            bucket["sync_conflicts"] += 1
        for row in quarantine_qs:
            bucket = by_farm[row.farm_id or 0]
            bucket["farm_id"] = row.farm_id
            bucket["farm_name"] = getattr(row.farm, "name", "")
            bucket["quarantined_payloads"] += 1
            if "mode" in str(row.variance_type or "").lower():
                bucket["mode_switch_quarantines"] += 1

        return {
            "generated_at": timezone.now().isoformat(),
            "sync_conflict_dlq_pending": conflict_qs.count(),
            "offline_sync_quarantine_pending": quarantine_qs.count(),
            "pending_mode_switch_quarantines": sum(row["mode_switch_quarantines"] for row in by_farm.values()),
            "farms": sorted(
                by_farm.values(),
                key=lambda row: (
                    -(row["sync_conflicts"] + row["quarantined_payloads"]),
                    row["farm_name"],
                ),
            ),
        }

    @classmethod
    def _offline_alerts(cls, *, farm_id: int | None = None) -> list[dict]:
        snapshot = cls.offline_ops_snapshot(farm_id=farm_id)
        alerts = []
        for row in snapshot.get("farms", []):
            if row["sync_conflicts"]:
                alerts.append(
                    cls._make_alert(
                        kind="offline_sync_attention",
                        severity="attention",
                        farm_id=row["farm_id"],
                        scope_type="farm",
                        scope_id=str(row["farm_id"] or "global"),
                        canonical_reason="sync_conflict_dlq_pending",
                        deep_link=cls._deep_link(kind="offline_sync_attention", farm_id=row["farm_id"]),
                        source_snapshot={
                            "origin": "offline_ops",
                            "sync_conflicts": row["sync_conflicts"],
                            "quarantined_payloads": row["quarantined_payloads"],
                            "created_at": snapshot.get("generated_at"),
                        },
                        title=f"sync conflicts ({row['sync_conflicts']})",
                    )
                )
            if row["quarantined_payloads"]:
                alerts.append(
                    cls._make_alert(
                        kind="offline_sync_attention",
                        severity="critical" if row["mode_switch_quarantines"] else "attention",
                        farm_id=row["farm_id"],
                        scope_type="farm",
                        scope_id=str(row["farm_id"] or "global"),
                        canonical_reason="offline_sync_quarantine_pending",
                        deep_link=cls._deep_link(kind="offline_sync_attention", farm_id=row["farm_id"]),
                        source_snapshot={
                            "origin": "offline_ops",
                            "sync_conflicts": row["sync_conflicts"],
                            "quarantined_payloads": row["quarantined_payloads"],
                            "mode_switch_quarantines": row["mode_switch_quarantines"],
                            "created_at": snapshot.get("generated_at"),
                        },
                        title=f"offline quarantine ({row['quarantined_payloads']})",
                    )
                )
        return alerts

    @classmethod
    def _apply_receipts(cls, *, user, alerts: list[dict], include_acknowledged: bool) -> list[dict]:
        fingerprints = [item["fingerprint"] for item in alerts]
        receipts = {
            row.fingerprint: row
            for row in OpsAlertReceipt.objects.filter(actor=user, fingerprint__in=fingerprints)
        }
        now = timezone.now()
        filtered = []
        for item in alerts:
            receipt = receipts.get(item["fingerprint"])
            if receipt is not None:
                state = {
                    "status": receipt.status,
                    "snooze_until": receipt.snooze_until.isoformat() if receipt.snooze_until else None,
                    "note": receipt.note,
                    "updated_at": receipt.updated_at.isoformat(),
                }
                item["operator_state"] = state
                if receipt.status == OpsAlertReceipt.STATUS_ACKNOWLEDGED and not include_acknowledged:
                    continue
                if (
                    receipt.status == OpsAlertReceipt.STATUS_SNOOZED
                    and receipt.snooze_until
                    and receipt.snooze_until > now
                    and not include_acknowledged
                ):
                    continue
            else:
                item["operator_state"] = {"status": "active"}
            filtered.append(item)
        filtered.sort(
            key=lambda item: (
                cls.SEVERITY_ORDER.get(item.get("severity"), 99),
                item.get("created_at") or "",
                item.get("fingerprint") or "",
            )
        )
        return filtered

    @classmethod
    def alerts_snapshot(
        cls,
        *,
        user,
        farm_id: int | None = None,
        include_acknowledged: bool = False,
        limit: int = 25,
    ) -> dict:
        if not cls._has_operator_access(user=user):
            return {
                "generated_at": timezone.now().isoformat(),
                "count": 0,
                "items": [],
                "summary": {"by_kind": {}, "by_severity": {}, "operator_access": False},
            }
        deduped = {}
        for item in (
            cls._approval_alerts(farm_id=farm_id)
            + cls._attachment_alerts(farm_id=farm_id)
            + cls._outbox_alerts(farm_id=farm_id)
            + cls._release_alerts()
            + cls._offline_alerts(farm_id=farm_id)
        ):
            deduped[item["fingerprint"]] = item
        alerts = cls._apply_receipts(
            user=user,
            alerts=list(deduped.values()),
            include_acknowledged=include_acknowledged,
        )[: max(1, int(limit or 25))]
        return {
            "generated_at": timezone.now().isoformat(),
            "count": len(alerts),
            "items": alerts,
            "summary": {
                "by_kind": dict(Counter(item.get("kind") for item in alerts)),
                "by_severity": dict(Counter(item.get("severity") for item in alerts)),
                "operator_access": True,
            },
        }

    @classmethod
    def acknowledge_alert(
        cls,
        *,
        user,
        fingerprint: str,
        note: str = "",
        request_id: str | None = None,
        correlation_id: str | None = None,
    ) -> dict:
        cls._ensure_operator(user=user)
        if not str(fingerprint or "").strip():
            raise ValidationError({"fingerprint": "fingerprint is required."})
        receipt, _ = OpsAlertReceipt.objects.update_or_create(
            actor=user,
            fingerprint=str(fingerprint).strip(),
            defaults={
                "status": OpsAlertReceipt.STATUS_ACKNOWLEDGED,
                "snooze_until": None,
                "note": str(note or "").strip(),
            },
        )
        logger.info(
            "ops.alert.acknowledged",
            extra={
                "fingerprint": receipt.fingerprint,
                "actor_id": getattr(user, "id", None),
                "request_id": request_id,
                "correlation_id": correlation_id or receipt.fingerprint,
            },
        )
        return {
            "fingerprint": receipt.fingerprint,
            "status": receipt.status,
            "updated_at": receipt.updated_at.isoformat(),
            "note": receipt.note,
        }

    @classmethod
    def snooze_alert(
        cls,
        *,
        user,
        fingerprint: str,
        hours: int,
        note: str = "",
        request_id: str | None = None,
        correlation_id: str | None = None,
    ) -> dict:
        cls._ensure_operator(user=user)
        if not str(fingerprint or "").strip():
            raise ValidationError({"fingerprint": "fingerprint is required."})
        try:
            hours_value = int(hours)
        except (TypeError, ValueError):
            raise ValidationError({"hours": "hours must be one of 1, 4, 24."})
        if hours_value not in cls.SNOOZE_PRESETS_HOURS:
            raise ValidationError({"hours": "hours must be one of 1, 4, 24."})
        snooze_until = timezone.now() + timedelta(hours=hours_value)
        receipt, _ = OpsAlertReceipt.objects.update_or_create(
            actor=user,
            fingerprint=str(fingerprint).strip(),
            defaults={
                "status": OpsAlertReceipt.STATUS_SNOOZED,
                "snooze_until": snooze_until,
                "note": str(note or "").strip(),
            },
        )
        logger.info(
            "ops.alert.snoozed",
            extra={
                "fingerprint": receipt.fingerprint,
                "actor_id": getattr(user, "id", None),
                "request_id": request_id,
                "correlation_id": correlation_id or receipt.fingerprint,
                "snooze_until": receipt.snooze_until.isoformat() if receipt.snooze_until else None,
            },
        )
        return {
            "fingerprint": receipt.fingerprint,
            "status": receipt.status,
            "snooze_until": receipt.snooze_until.isoformat() if receipt.snooze_until else None,
            "updated_at": receipt.updated_at.isoformat(),
            "note": receipt.note,
        }

    @classmethod
    def outbox_trace(
        cls,
        *,
        user,
        event_id: str | None = None,
        correlation_id: str | None = None,
        request_id: str | None = None,
    ) -> dict:
        cls._ensure_operator(user=user)
        if not event_id and not correlation_id:
            raise ValidationError({"detail": "event_id or correlation_id is required."})
        queryset = IntegrationOutboxEvent.objects.select_related("farm", "created_by")
        event = None
        if event_id:
            event = queryset.filter(Q(pk=event_id) | Q(event_id=str(event_id))).order_by("-created_at").first()
        if event is None and correlation_id:
            event = queryset.filter(
                Q(metadata__correlation_id=str(correlation_id)) | Q(event_id=str(correlation_id))
            ).order_by("-created_at").first()
        if event is None:
            raise ValidationError({"detail": "outbox event not found."})
        resolved_correlation = (event.metadata or {}).get("correlation_id") or correlation_id or event.event_id
        related = queryset.filter(
            Q(event_id=event.event_id) | Q(metadata__correlation_id=resolved_correlation)
        ).order_by("created_at", "id")
        rows = [
            {
                "id": row.id,
                "event_id": row.event_id,
                "event_type": row.event_type,
                "aggregate_type": row.aggregate_type,
                "aggregate_id": row.aggregate_id,
                "destination": row.destination,
                "farm_id": row.farm_id,
                "farm_name": getattr(row.farm, "name", ""),
                "status": row.status,
                "attempts": row.attempts,
                "max_attempts": row.max_attempts,
                "available_at": row.available_at.isoformat() if row.available_at else None,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                "dispatched_at": row.dispatched_at.isoformat() if row.dispatched_at else None,
                "last_error": row.last_error,
                "retry_eligible": row.status != IntegrationOutboxEvent.Status.DISPATCHED,
                "correlation_id": (row.metadata or {}).get("correlation_id") or row.event_id,
                "metadata": row.metadata or {},
            }
            for row in related
        ]
        logger.info(
            "ops.trace.viewed",
            extra={
                "trace_kind": "outbox",
                "event_id": event.event_id,
                "actor_id": getattr(user, "id", None),
                "request_id": request_id,
                "correlation_id": resolved_correlation,
            },
        )
        return {
            "trace_kind": "outbox",
            "generated_at": timezone.now().isoformat(),
            "event": rows[-1] if rows else {},
            "timeline": rows,
            "correlation_id": resolved_correlation,
            "request_headers": {"request_id": "X-Request-Id", "correlation_id": "X-Correlation-Id"},
        }

    @classmethod
    def attachment_trace(
        cls,
        *,
        user,
        attachment_id: int,
        request_id: str | None = None,
        correlation_id: str | None = None,
    ) -> dict:
        cls._ensure_operator(user=user)
        try:
            attachment = Attachment.objects.select_related("farm", "uploaded_by").get(
                pk=int(attachment_id),
                deleted_at__isnull=True,
            )
        except (Attachment.DoesNotExist, TypeError, ValueError):
            raise ValidationError({"attachment_id": "attachment not found."})
        lifecycle = list(
            AttachmentLifecycleEvent.objects.filter(attachment=attachment)
            .select_related("actor")
            .values(
                "id",
                "action",
                "note",
                "metadata",
                "created_at",
                "actor_id",
                "actor__username",
            )
        )
        logger.info(
            "ops.trace.viewed",
            extra={
                "trace_kind": "attachment",
                "attachment_id": attachment.id,
                "actor_id": getattr(user, "id", None),
                "request_id": request_id,
                "correlation_id": correlation_id or f"attachment-{attachment.id}",
            },
        )
        return {
            "trace_kind": "attachment",
            "generated_at": timezone.now().isoformat(),
            "attachment": {
                "id": attachment.id,
                "name": attachment.name or attachment.filename_original or attachment.file.name,
                "farm_id": attachment.farm_id,
                "farm_name": getattr(attachment.farm, "name", ""),
                "evidence_class": attachment.evidence_class,
                "scan_state": attachment.scan_state,
                "archive_state": attachment.archive_state,
                "quarantine_state": attachment.quarantine_state,
                "authoritative_at": attachment.authoritative_at.isoformat() if attachment.authoritative_at else None,
                "archived_at": attachment.archived_at.isoformat() if attachment.archived_at else None,
                "quarantined_at": attachment.quarantined_at.isoformat() if attachment.quarantined_at else None,
                "quarantine_reason": attachment.quarantine_reason,
                "canonical_reason": OpsHealthService._attachment_risk_reason(attachment=attachment),
                "uploaded_by": getattr(attachment.uploaded_by, "username", ""),
            },
            "lifecycle_events": lifecycle,
            "correlation_id": correlation_id or f"attachment-{attachment.id}",
            "request_headers": {"request_id": "X-Request-Id", "correlation_id": "X-Correlation-Id"},
        }
