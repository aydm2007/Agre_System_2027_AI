from __future__ import annotations

import hashlib
from pathlib import Path
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models import Asset, Attachment, AttachmentLifecycleEvent, DailyLog, Farm, FuelConsumptionAlert, Supervisor
from smart_agri.core.models.settings import FarmSettings
from smart_agri.core.services.attachment_policy_service import AttachmentPolicyService
from smart_agri.core.services.fixed_asset_lifecycle_service import FixedAssetLifecycleService
from smart_agri.core.services.fuel_reconciliation_posting_service import FuelReconciliationPostingService
from smart_agri.core.services.remote_review_service import RemoteReviewService
from smart_agri.finance.models import ApprovalRequest, ApprovalRule
from smart_agri.finance.services.approval_service import ApprovalGovernanceService
from smart_agri.integration_hub.event_contracts import ActivityLogged, FinancialTransactionCreated, InventoryChanged
from smart_agri.integration_hub.persistence import persist_event
from smart_agri.inventory.models import FuelLog, TankCalibration


class Command(BaseCommand):
    help = "Seed governed runtime evidence for approvals, attachments, outbox, fixed assets, and fuel reconciliation."

    @staticmethod
    def _ensure_alive(instance):
        """Restore a soft-deleted record so downstream services can find it."""
        if instance.deleted_at is not None or not instance.is_active:
            instance.deleted_at = None
            instance.is_active = True
            instance.save(update_fields=["deleted_at", "is_active", "updated_at"])
        return instance

    @staticmethod
    def _attachment_file_exists(attachment: Attachment) -> bool:
        file_field = getattr(attachment, "file", None)
        file_name = getattr(file_field, "name", "")
        if not file_field or not file_name:
            return False
        try:
            return Path(file_field.path).exists()
        except (NotImplementedError, ValueError, OSError):
            return False

    @staticmethod
    def _seed_failure(*, scope: str, farm: Farm, identifier: str, details: str) -> CommandError:
        farm_ref = getattr(farm, "slug", None) or getattr(farm, "pk", None) or "unknown"
        return CommandError(f"{scope} runtime seed failed for farm={farm_ref} identifier={identifier}: {details}")

    def _ensure_seed_asset(self, *, farm: Farm, code: str, defaults: dict) -> Asset:
        asset = Asset.objects.filter(farm=farm, code=code).order_by("deleted_at", "id").first()
        if asset is None:
            asset = Asset.objects.create(farm=farm, code=code, **defaults)
        else:
            update_fields = []
            for field, value in defaults.items():
                if getattr(asset, field) != value:
                    setattr(asset, field, value)
                    update_fields.append(field)
            if asset.deleted_at is not None or not asset.is_active:
                asset.deleted_at = None
                asset.is_active = True
                update_fields.extend(["deleted_at", "is_active"])
            if update_fields:
                asset.save(update_fields=list(dict.fromkeys([*update_fields, "updated_at"])))

        live_asset = Asset.objects.filter(pk=asset.pk, deleted_at__isnull=True, is_active=True).first()
        if live_asset is None:
            raise self._seed_failure(
                scope="fixed_assets",
                farm=farm,
                identifier=code,
                details="asset row could not be reloaded as an active, non-deleted record before posting",
            )
        return live_asset

    def _assert_attachment_state(self, *, farm: Farm, attachment: Attachment, name: str, expected: dict):
        attachment.refresh_from_db()
        failures = []
        for field, value in expected.items():
            actual = getattr(attachment, field)
            if callable(value):
                if not value(actual):
                    failures.append(f"{field}={actual!r}")
            elif actual != value:
                failures.append(f"{field}={actual!r}")
        if failures:
            raise self._seed_failure(
                scope="attachments",
                farm=farm,
                identifier=name,
                details="attachment state mismatch after seeding: " + ", ".join(failures),
            )

    def _assert_attachment_events(self, *, farm: Farm, attachment: Attachment, name: str, required_actions: tuple[str, ...]):
        observed_actions = set(
            AttachmentLifecycleEvent.objects.filter(attachment=attachment).values_list("action", flat=True)
        )
        missing_actions = [action for action in required_actions if action not in observed_actions]
        if missing_actions:
            raise self._seed_failure(
                scope="attachments",
                farm=farm,
                identifier=name,
                details="missing lifecycle evidence: " + ", ".join(missing_actions),
            )

    def handle(self, *args, **options):
        users = self._ensure_users()
        strict_farm, strict_settings = self._ensure_strict_farm(users)
        remote_farm = self._ensure_remote_small_farm(users)
        self._seed_fixed_assets(users=users, farm=strict_farm)
        self._seed_fuel_reconciliation(users=users, farm=strict_farm)
        self._seed_approvals(users=users, farm=strict_farm)
        self._seed_attachments(users=users, farm=strict_farm)
        self._seed_outbox(farm=strict_farm, created_by=users["manager"])
        self._seed_remote_reviews(users=users, remote_farm=remote_farm)
        strict_settings.refresh_from_db()
        self.stdout.write(self.style.SUCCESS("Seeded governed runtime evidence for readiness and runtime probes."))

    def _ensure_users(self):
        User = get_user_model()
        specs = {
            "manager": ("evidence_manager", "مدير المزرعة"),
            "farm_finance": ("evidence_farm_finance", "المدير المالي للمزرعة"),
            "sector_accountant": ("evidence_sector_accountant", "محاسب القطاع"),
            "sector_reviewer": ("evidence_sector_reviewer", "مراجع القطاع"),
            "chief_accountant": ("evidence_sector_chief", "رئيس حسابات القطاع"),
            "finance_director": ("evidence_finance_director", "المدير المالي لقطاع المزارع"),
            "sector_director": ("evidence_sector_director", "مدير القطاع"),
        }
        users = {}
        for key, (username, _role) in specs.items():
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={"is_staff": True, "is_superuser": key == "sector_director"},
            )
            if not user.is_staff:
                user.is_staff = True
                user.save(update_fields=["is_staff"])
            users[key] = user
        return users

    def _ensure_strict_farm(self, users):
        farm, _ = Farm.objects.get_or_create(
            slug="strict-evidence-farm",
            defaults={
                "name": "Strict Evidence Farm",
                "region": "Sanaa",
                "tier": Farm.TIER_MEDIUM,
                "is_organization": False,
                "operational_mode": FarmSettings.MODE_STRICT,
                "sensing_mode": "MANUAL",
                "organization_id": None,
            },
        )
        farm_update_fields = []
        if farm.tier != Farm.TIER_MEDIUM:
            farm.tier = Farm.TIER_MEDIUM
            farm_update_fields.append("tier")
        if farm.operational_mode != FarmSettings.MODE_STRICT:
            farm.operational_mode = FarmSettings.MODE_STRICT
            farm_update_fields.append("operational_mode")
        if farm.sensing_mode != "MANUAL":
            farm.sensing_mode = "MANUAL"
            farm_update_fields.append("sensing_mode")
        if farm_update_fields:
            farm.save(update_fields=[*farm_update_fields, "updated_at"])
        settings_obj, _ = FarmSettings.objects.get_or_create(farm=farm)
        settings_obj.mode = FarmSettings.MODE_STRICT
        settings_obj.cost_visibility = FarmSettings.COST_VISIBILITY_FULL
        settings_obj.fixed_asset_mode = FarmSettings.FIXED_ASSET_MODE_FULL_CAPITALIZATION
        settings_obj.approval_profile = FarmSettings.APPROVAL_PROFILE_STRICT_FINANCE
        settings_obj.contract_mode = FarmSettings.CONTRACT_MODE_FULL_ERP
        settings_obj.treasury_visibility = FarmSettings.TREASURY_VISIBILITY_VISIBLE
        settings_obj.weekly_remote_review_required = False
        settings_obj.remote_site = False
        settings_obj.save()
        memberships = {
            users["manager"]: "مدير المزرعة",
            users["farm_finance"]: "المدير المالي للمزرعة",
            users["sector_accountant"]: "محاسب القطاع",
            users["sector_reviewer"]: "مراجع القطاع",
            users["chief_accountant"]: "رئيس حسابات القطاع",
            users["finance_director"]: "المدير المالي لقطاع المزارع",
            users["sector_director"]: "مدير القطاع",
        }
        for user, role in memberships.items():
            FarmMembership.objects.update_or_create(user=user, farm=farm, defaults={"role": role})
        return farm, settings_obj

    def _ensure_remote_small_farm(self, users):
        farm, _ = Farm.objects.get_or_create(
            slug="remote-review-farm",
            defaults={
                "name": "Remote Review Farm",
                "region": "Saada",
                "tier": Farm.TIER_SMALL,
                "is_organization": False,
                "operational_mode": FarmSettings.MODE_SIMPLE,
                "sensing_mode": "MANUAL",
                "organization_id": None,
            },
        )
        farm_update_fields = []
        if farm.tier != Farm.TIER_SMALL:
            farm.tier = Farm.TIER_SMALL
            farm_update_fields.append("tier")
        if farm.operational_mode != FarmSettings.MODE_SIMPLE:
            farm.operational_mode = FarmSettings.MODE_SIMPLE
            farm_update_fields.append("operational_mode")
        if farm.sensing_mode != "MANUAL":
            farm.sensing_mode = "MANUAL"
            farm_update_fields.append("sensing_mode")
        if farm_update_fields:
            farm.save(update_fields=[*farm_update_fields, "updated_at"])
        settings_obj, _ = FarmSettings.objects.get_or_create(farm=farm)
        settings_obj.mode = FarmSettings.MODE_SIMPLE
        settings_obj.remote_site = True
        settings_obj.weekly_remote_review_required = True
        settings_obj.single_finance_officer_allowed = True
        settings_obj.remote_review_interval_days = 7
        settings_obj.remote_review_overdue_grace_days = 0
        settings_obj.save()
        FarmMembership.objects.update_or_create(
            user=users["manager"],
            farm=farm,
            defaults={"role": "مدير المزرعة"},
        )
        return farm

    def _seed_fixed_assets(self, *, users, farm):
        asset = self._ensure_seed_asset(
            farm=farm,
            code="EVID-SOLAR-1",
            defaults={
                "category": "Solar",
                "asset_type": "solar_array",
                "name": "Evidence Solar Array",
                "purchase_value": Decimal("150000.00"),
                "salvage_value": Decimal("15000.00"),
                "accumulated_depreciation": Decimal("25000.00"),
                "useful_life_years": 12,
            },
        )
        self._ensure_seed_asset(
            farm=farm,
            code="EVID-TRACTOR-1",
            defaults={
                "category": "Machinery",
                "asset_type": "tractor",
                "name": "Evidence Tractor",
                "purchase_value": Decimal("90000.00"),
                "salvage_value": Decimal("5000.00"),
                "accumulated_depreciation": Decimal("10000.00"),
                "useful_life_years": 8,
                "operational_cost_per_hour": Decimal("275.00"),
            },
        )
        from smart_agri.core.models import AuditLog
        if AuditLog.objects.filter(action="FIXED_ASSET_CAPITALIZE", object_id=str(asset.pk)).exists():
            return

        live_asset = Asset.objects.filter(pk=asset.pk, deleted_at__isnull=True, is_active=True).first()
        if live_asset is None:
            raise self._seed_failure(
                scope="fixed_assets",
                farm=farm,
                identifier="EVID-SOLAR-1",
                details="capitalization preflight could not reload a live asset row",
            )

        try:
            FixedAssetLifecycleService.capitalize_asset(
                user=users["finance_director"],
                asset_id=live_asset.pk,
                capitalized_value=Decimal("150000.00"),
                reason="seeded_runtime_evidence",
                ref_id="SEED-FA-CAP",
            )
        except (Asset.DoesNotExist, ValidationError, ValueError) as exc:
            raise self._seed_failure(
                scope="fixed_assets",
                farm=farm,
                identifier="EVID-SOLAR-1",
                details=str(exc),
            ) from exc

    def _seed_fuel_reconciliation(self, *, users, farm):
        supervisor = Supervisor.objects.filter(farm=farm, code="EVID-SUP").order_by("deleted_at", "id").first()
        if supervisor is None:
            supervisor = Supervisor.objects.create(farm=farm, code="EVID-SUP", name="Evidence Supervisor")
        self._ensure_alive(supervisor)
        tank = self._ensure_seed_asset(farm=farm, code="EVID-TANK-1", defaults={"category": "Fuel", "asset_type": "tank", "name": "Evidence Diesel Tank"})
        machine = self._ensure_seed_asset(farm=farm, code="EVID-MACH-1", defaults={"category": "Machinery", "asset_type": "tractor", "name": "Evidence Field Tractor"})
        TankCalibration.objects.get_or_create(asset=tank, cm_reading=Decimal("90.00"), defaults={"liters_volume": Decimal("90.0000")})
        TankCalibration.objects.get_or_create(asset=tank, cm_reading=Decimal("100.00"), defaults={"liters_volume": Decimal("100.0000")})
        fuel_log = FuelLog.objects.filter(farm=farm, asset_tank=tank).order_by("-id").first()
        if fuel_log is None:
            fuel_log = FuelLog.objects.create(
                farm=farm,
                asset_tank=tank,
                supervisor=supervisor,
                reading_date=timezone.now(),
                measurement_method=FuelLog.MEASUREMENT_METHOD_DIPSTICK,
                reading_start_cm=Decimal("100.00"),
                reading_end_cm=Decimal("90.00"),
            )
        daily_log, _ = DailyLog.objects.get_or_create(
            farm=farm,
            supervisor=supervisor,
            log_date=fuel_log.reading_date.date(),
            defaults={"fuel_alert_status": DailyLog.FUEL_ALERT_STATUS_WARNING},
        )
        if daily_log.fuel_alert_status == DailyLog.FUEL_ALERT_STATUS_OK:
            daily_log.fuel_alert_status = DailyLog.FUEL_ALERT_STATUS_WARNING
            daily_log.save(update_fields=["fuel_alert_status"])
        FuelConsumptionAlert.objects.get_or_create(
            log=daily_log,
            asset=machine,
            defaults={
                "machine_hours": Decimal("1.00"),
                "actual_liters": Decimal("10.0000"),
                "expected_liters": Decimal("8.0000"),
                "deviation_pct": Decimal("25.00"),
                "status": FuelConsumptionAlert.STATUS_WARNING,
                "note": "seeded_runtime_warning",
            },
        )
        from smart_agri.core.models import AuditLog
        if not AuditLog.objects.filter(action="FUEL_RECONCILIATION_POST", object_id=str(fuel_log.pk)).exists():
            FuelReconciliationPostingService.approve_and_post(
                user=users["finance_director"],
                daily_log_id=daily_log.pk,
                fuel_log_id=fuel_log.pk,
                reason="seeded_runtime_reconciliation",
                ref_id="SEED-FUEL-POST",
            )

    def _seed_approvals(self, *, users, farm):
        base_amount = Decimal("2200000.0000")
        final_request = self._request_by_action(
            farm=farm,
            action="contract_payment_posting",
            amount=base_amount,
            requested_by=users["manager"],
        )
        self._advance_if_pending(final_request, users["farm_finance"])
        self._advance_if_pending(final_request, users["sector_accountant"])
        self._advance_if_pending(final_request, users["sector_reviewer"])
        self._advance_if_pending(final_request, users["chief_accountant"])
        self._advance_if_pending(final_request, users["finance_director"])
        self._advance_if_pending(final_request, users["sector_director"])

        rejected_request = self._request_by_action(
            farm=farm,
            action="petty_cash_settlement",
            amount=Decimal("120000.0000"),
            requested_by=users["manager"],
        )
        if rejected_request.status == ApprovalRequest.STATUS_PENDING and not rejected_request.rejection_reason:
            try:
                ApprovalGovernanceService.reject_request(
                    user=users["farm_finance"],
                    request_id=rejected_request.pk,
                    reason="seeded_rejection",
                )
            except ValidationError:
                pass
        rejected_request.refresh_from_db()
        if rejected_request.status == ApprovalRequest.STATUS_REJECTED:
            try:
                ApprovalGovernanceService.reopen_request(
                    user=users["manager"],
                    request_id=rejected_request.pk,
                    reason="seeded_reopen",
                )
            except ValidationError:
                pass

        pending_sector = self._request_by_action(
            farm=farm,
            action="supplier_settlement",
            amount=Decimal("350000.0000"),
            requested_by=users["manager"],
        )
        self._advance_if_pending(pending_sector, users["farm_finance"])

        pending_review = self._request_by_action(
            farm=farm,
            action="fuel_reconciliation",
            amount=Decimal("650000.0000"),
            requested_by=users["manager"],
        )
        self._advance_if_pending(pending_review, users["farm_finance"])
        self._advance_if_pending(pending_review, users["sector_accountant"])

        overdue_request = self._request_by_action(
            farm=farm,
            action="fixed_asset_posting",
            amount=Decimal("180000.0000"),
            requested_by=users["manager"],
        )
        if overdue_request.status == ApprovalRequest.STATUS_PENDING and overdue_request.current_stage == 1:
            ApprovalRequest.objects.filter(pk=overdue_request.pk).update(updated_at=timezone.now() - timedelta(days=4))
            ApprovalGovernanceService.escalate_overdue_requests()

    def _request_by_action(self, *, farm, action, amount, requested_by):
        req = ApprovalRequest.objects.filter(farm=farm, action=action, requested_amount=amount, deleted_at__isnull=True).first()
        if req:
            return req
        return ApprovalGovernanceService.create_request(
            user=requested_by,
            farm=farm,
            module=ApprovalRule.MODULE_FINANCE,
            action=action,
            requested_amount=amount,
        )

    def _advance_if_pending(self, req, user):
        req.refresh_from_db()
        if req.status == ApprovalRequest.STATUS_PENDING and ApprovalGovernanceService.can_approve(user, req):
            ApprovalGovernanceService.approve_request(user=user, request_id=req.pk, note="seeded_stage_progress")

    def _seed_attachments(self, *, users, farm):
        clean = self._attachment(
            farm=farm,
            user=users["manager"],
            name="seed_clean_evidence.pdf",
            content=b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF",
            related_document_type="approval_evidence",
        )
        quarantine = self._attachment(
            farm=farm,
            user=users["manager"],
            name="seed_suspicious_evidence.pdf",
            content=b"%PDF-1.4\n/OpenAction << /S /JavaScript /JS (app.alert('x')) >>\n%%EOF",
            related_document_type="approval_evidence",
        )
        transient = self._attachment(
            farm=farm,
            user=users["manager"],
            name="seed_draft.csv",
            content=b"col1,col2\n1,2\n",
            related_document_type="draft_support",
            evidence_class=Attachment.EVIDENCE_CLASS_TRANSIENT,
            content_type="text/csv",
        )

        settings_obj = farm.settings

        if clean.malware_scan_status != Attachment.MALWARE_SCAN_PASSED:
            AttachmentPolicyService.scan_attachment(attachment=clean, farm_settings=settings_obj)
            clean.save()
        if not clean.is_authoritative_evidence:
            AttachmentPolicyService.mark_authoritative_after_approval(attachment=clean, farm_settings=settings_obj)
            clean.save()
        if clean.storage_tier != Attachment.STORAGE_TIER_ARCHIVE:
            AttachmentPolicyService.move_to_archive(attachment=clean)
            clean.save()
        if clean.evidence_class != Attachment.EVIDENCE_CLASS_LEGAL_HOLD:
            AttachmentPolicyService.apply_legal_hold(attachment=clean)
            clean.save()
        if clean.restored_at is None:
            AttachmentPolicyService.restore_from_archive(attachment=clean)
            AttachmentPolicyService.release_legal_hold(attachment=clean)
            clean.save()

        if quarantine.malware_scan_status != Attachment.MALWARE_SCAN_QUARANTINED:
            AttachmentPolicyService.scan_attachment(attachment=quarantine, farm_settings=settings_obj)
            quarantine.save()

        if transient.deleted_at is None:
            transient.expires_at = timezone.now() - timedelta(days=1)
            transient.save()
            AttachmentPolicyService.purge_transient(attachment=transient)
            transient.save()

        self._assert_attachment_state(
            farm=farm,
            attachment=clean,
            name="seed_clean_evidence.pdf",
            expected={
                "malware_scan_status": Attachment.MALWARE_SCAN_PASSED,
                "is_authoritative_evidence": True,
                "storage_tier": lambda value: value in {Attachment.STORAGE_TIER_HOT, Attachment.STORAGE_TIER_ARCHIVE},
                "archive_key": lambda value: bool(value),
                "restored_at": lambda value: value is not None,
            },
        )
        self._assert_attachment_events(
            farm=farm,
            attachment=clean,
            name="seed_clean_evidence.pdf",
            required_actions=(
                AttachmentLifecycleEvent.ACTION_SCAN_PASSED,
                AttachmentLifecycleEvent.ACTION_AUTHORITATIVE_MARKED,
                AttachmentLifecycleEvent.ACTION_ARCHIVED,
                AttachmentLifecycleEvent.ACTION_LEGAL_HOLD_APPLIED,
                AttachmentLifecycleEvent.ACTION_RESTORED,
                AttachmentLifecycleEvent.ACTION_LEGAL_HOLD_RELEASED,
            ),
        )
        self._assert_attachment_state(
            farm=farm,
            attachment=quarantine,
            name="seed_suspicious_evidence.pdf",
            expected={
                "malware_scan_status": Attachment.MALWARE_SCAN_QUARANTINED,
                "quarantined_at": lambda value: value is not None,
            },
        )
        self._assert_attachment_events(
            farm=farm,
            attachment=quarantine,
            name="seed_suspicious_evidence.pdf",
            required_actions=(AttachmentLifecycleEvent.ACTION_SCAN_QUARANTINED,),
        )
        self._assert_attachment_state(
            farm=farm,
            attachment=transient,
            name="seed_draft.csv",
            expected={
                "deleted_at": lambda value: value is not None,
                "is_authoritative_evidence": False,
            },
        )
        self._assert_attachment_events(
            farm=farm,
            attachment=transient,
            name="seed_draft.csv",
            required_actions=(AttachmentLifecycleEvent.ACTION_PURGED,),
        )

    def _attachment(self, *, farm, user, name, content, related_document_type, evidence_class=None, content_type="application/pdf"):
        checksum = hashlib.sha256(content).hexdigest()
        attachment = Attachment.objects.filter(farm=farm, filename_original=name).order_by("deleted_at", "id").first()
        expected_class = evidence_class or Attachment.EVIDENCE_CLASS_OPERATIONAL
        if attachment and attachment.sha256_checksum == checksum and attachment.deleted_at is None and self._attachment_file_exists(attachment):
            return attachment

        upload = SimpleUploadedFile(name, content, content_type=content_type)
        try:
            if attachment is None:
                return Attachment.objects.create(
                    file=upload,
                    name=name,
                    evidence_class=expected_class,
                    attachment_class=expected_class,
                    retention_class=expected_class,
                    content_type=content_type,
                    sha256_checksum=checksum,
                    size=len(content),
                    uploaded_by=user,
                    farm=farm,
                    related_document_type=related_document_type,
                    filename_original=name,
                    mime_type_detected=content_type,
                    content_hash=checksum,
                    size_bytes=len(content),
                )

            attachment.file = upload
            attachment.name = name
            attachment.evidence_class = expected_class
            attachment.attachment_class = expected_class
            attachment.retention_class = expected_class
            attachment.content_type = content_type
            attachment.sha256_checksum = checksum
            attachment.size = len(content)
            attachment.uploaded_by = user
            attachment.farm = farm
            attachment.related_document_type = related_document_type
            attachment.filename_original = name
            attachment.mime_type_detected = content_type
            attachment.content_hash = checksum
            attachment.size_bytes = len(content)
            attachment.deleted_at = None
            attachment.deleted_by = None
            attachment.is_active = True
            attachment.expires_at = None
            attachment.archived_at = None
            attachment.storage_tier = Attachment.STORAGE_TIER_HOT
            attachment.archive_backend = ""
            attachment.archive_key = ""
            attachment.malware_scan_status = Attachment.MALWARE_SCAN_PENDING
            attachment.scan_state = Attachment.MALWARE_SCAN_PENDING
            attachment.quarantine_reason = ""
            attachment.scanned_at = None
            attachment.quarantined_at = None
            attachment.restored_at = None
            attachment.is_authoritative_evidence = False
            attachment.authoritative_at = None
            attachment.save()
            return attachment
        finally:
            upload.close()

    def _seed_outbox(self, *, farm, created_by):
        from smart_agri.core.models import IntegrationOutboxEvent

        seed_flag = {"seed_runtime_governance": True}
        expected_ids = {
            "seed-readiness-success",
            "seed-readiness-dispatched",
            "seed-readiness-retry",
            "seed-readiness-dead-letter",
        }
        IntegrationOutboxEvent.objects.filter(metadata__seed_runtime_governance=True).exclude(event_id__in=expected_ids).delete()
        event_specs = [
            (
                ActivityLogged(
                    aggregate_id="seed-activity-success",
                    activity_type="irrigation",
                    quantity=3,
                    farm_id=str(farm.id),
                    event_id="seed-readiness-success",
                    metadata=seed_flag,
                ),
                "readiness/success",
            ),
            (
                ActivityLogged(
                    aggregate_id="seed-activity-dispatched",
                    activity_type="fertilization",
                    quantity=1,
                    farm_id=str(farm.id),
                    event_id="seed-readiness-dispatched",
                    metadata=seed_flag,
                ),
                "readiness/already-dispatched",
            ),
            (
                FinancialTransactionCreated(
                    aggregate_id="seed-fin-retry",
                    amount="2500.00",
                    farm_id=str(farm.id),
                    event_id="seed-readiness-retry",
                    metadata=seed_flag,
                ),
                "readiness/retry",
            ),
            (
                InventoryChanged(
                    aggregate_id="seed-item-dead",
                    sku="DIESEL",
                    delta_quantity=-10,
                    farm_id=str(farm.id),
                    event_id="seed-readiness-dead-letter",
                    metadata=seed_flag,
                ),
                "readiness/dead-letter",
            ),
        ]
        for event, destination in event_specs:
            row = IntegrationOutboxEvent.objects.filter(event_id=event.event_id).first()
            if row is None:
                row = persist_event(event, destination=destination, farm_id=farm.id, created_by_id=created_by.id)
            elif row.destination != destination:
                row.destination = destination
            if row.metadata.get("seed_runtime_governance") is not True:
                row.metadata = {**row.metadata, **seed_flag}
            if event.event_id == "seed-readiness-dispatched" and row.status != IntegrationOutboxEvent.Status.DISPATCHED:
                row.status = IntegrationOutboxEvent.Status.DISPATCHED
                row.dispatched_at = timezone.now() - timedelta(minutes=2)
                row.last_error = ""
                row.attempts = 0
                row.available_at = timezone.now() - timedelta(minutes=2)
                row.save(update_fields=["destination", "status", "dispatched_at", "last_error", "attempts", "available_at", "metadata", "updated_at"])
                continue
            if event.event_id == "seed-readiness-retry":
                row.status = IntegrationOutboxEvent.Status.FAILED
                row.attempts = 1
                row.last_error = "readiness_retryable_failure"
                row.available_at = timezone.now() - timedelta(minutes=1)
                row.dispatched_at = None
                row.save(update_fields=["destination", "status", "attempts", "last_error", "available_at", "dispatched_at", "metadata", "updated_at"])
                continue
            if event.event_id == "seed-readiness-dead-letter":
                row.status = IntegrationOutboxEvent.Status.DEAD_LETTER
                row.attempts = row.max_attempts
                row.last_error = "readiness_dead_letter_failure"
                row.available_at = timezone.now() - timedelta(minutes=1)
                row.dispatched_at = None
                row.save(update_fields=["destination", "status", "attempts", "last_error", "available_at", "dispatched_at", "metadata", "updated_at"])
                continue
            row.status = IntegrationOutboxEvent.Status.PENDING
            row.attempts = 0
            row.last_error = ""
            row.available_at = timezone.now() - timedelta(minutes=1)
            row.dispatched_at = None
            row.save(update_fields=["destination", "status", "attempts", "last_error", "available_at", "dispatched_at", "metadata", "updated_at"])

    def _seed_remote_reviews(self, *, users, remote_farm):
        settings_obj = remote_farm.settings
        RemoteReviewService.overdue_farms()
        old_review = RemoteReviewService.last_review(remote_farm.id)
        if old_review is None:
            old_review = RemoteReviewService.record_review(
                farm=remote_farm,
                reviewer=users["sector_director"],
                notes="seeded_old_review",
                exceptions_found=2,
            )
            old_review.reviewed_at = timezone.now() - timedelta(days=20)
            old_review.save(update_fields=["reviewed_at"])
