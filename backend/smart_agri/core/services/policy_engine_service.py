from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
import logging

from django.core.exceptions import ValidationError
from django.db import DatabaseError, OperationalError, ProgrammingError, connection, models, transaction
from django.utils import timezone

from smart_agri.core.api.permissions import user_has_sector_finance_authority
from smart_agri.core.models.settings import FarmSettings
from smart_agri.core.models.policy_engine import (
    FarmPolicyBinding,
    PolicyActivationEvent,
    PolicyActivationRequest,
    PolicyExceptionEvent,
    PolicyExceptionRequest,
    PolicyPackage,
    PolicyVersion,
)

logger = logging.getLogger(__name__)


class PolicyEngineService:
    POLICY_ENGINE_TABLES = {
        "core_policypackage",
        "core_policyversion",
        "core_farmpolicybinding",
        "core_policyactivationrequest",
        "core_policyactivationevent",
        "core_policyexceptionrequest",
        "core_policyexceptionevent",
    }
    _schema_availability_cache: dict[str, bool] = {}

    SECTION_FIELDS = {
        "dual_mode_policy": [
            "mode",
            "variance_behavior",
            "cost_visibility",
            "approval_profile",
            "contract_mode",
            "treasury_visibility",
            "fixed_asset_mode",
            "show_daily_log_smart_card",
        ],
        "finance_threshold_policy": [
            "procurement_committee_threshold",
            "single_finance_officer_allowed",
            "local_finance_threshold",
            "sector_review_threshold",
            "sales_tax_percentage",
        ],
        "attachment_policy": [
            "mandatory_attachment_for_cash",
            "attachment_transient_ttl_days",
            "approved_attachment_archive_after_days",
            "attachment_max_upload_size_mb",
            "attachment_scan_mode",
            "attachment_require_clean_scan_for_strict",
            "attachment_enable_cdr",
        ],
        "contract_policy": [
            "enable_sharecropping",
            "sharecropping_mode",
            "enable_petty_cash",
        ],
        "agronomy_execution_policy": [
            "enable_zakat",
            "enable_depreciation",
            "allow_overlapping_crop_plans",
            "allow_multi_location_activities",
            "allow_cross_plan_activities",
            "allow_creator_self_variance_approval",
        ],
        "remote_review_policy": [
            "remote_site",
            "weekly_remote_review_required",
        ],
    }

    COMPATIBILITY_PROJECTION_FIELDS = tuple(
        field
        for fields in SECTION_FIELDS.values()
        for field in fields
    )

    DEFAULT_ELIGIBILITY_WARNINGS = {
        "strict_mode_transition": "Activating STRICT mode will tighten governed route access and may quarantine pending risky work.",
        "remote_review_enforced": "Remote-review enforcement becomes active; overdue weekly review windows may block strict finance actions.",
        "attachment_clean_scan": "STRICT evidence flows will require clean scan outcomes before authoritative evidence can pass.",
        "policy_binding_replace": "Applying this request will retire the currently active binding and replace it with the new effective policy.",
    }
    EXCEPTION_ELIGIBLE_FIELDS = {
        "procurement_committee_threshold",
        "local_finance_threshold",
        "sector_review_threshold",
        "sales_tax_percentage",
        "mandatory_attachment_for_cash",
        "attachment_transient_ttl_days",
        "approved_attachment_archive_after_days",
        "attachment_max_upload_size_mb",
        "attachment_scan_mode",
        "attachment_require_clean_scan_for_strict",
        "attachment_enable_cdr",
        "remote_site",
        "weekly_remote_review_required",
        "enable_petty_cash",
        "enable_sharecropping",
        "show_daily_log_smart_card",
        "allow_creator_self_variance_approval",
    }

    @staticmethod
    def _require_sector_central_authority(user) -> None:
        if getattr(user, "is_superuser", False):
            return
        if user.has_perm("finance.can_sector_finance_approve") or user_has_sector_finance_authority(user):
            return
        raise ValidationError("Policy engine mutation requires sector-central governance authority.")

    @classmethod
    def default_policy_payload(cls) -> dict:
        settings = FarmSettings()
        return cls.policy_payload_from_settings(settings=settings)

    @classmethod
    def policy_payload_from_settings(cls, *, settings: FarmSettings) -> dict:
        payload = {}
        for section, fields in cls.SECTION_FIELDS.items():
            payload[section] = {field: getattr(settings, field) for field in fields}
        return payload

    @classmethod
    def flatten_policy_payload(cls, payload: dict | None) -> dict:
        payload = payload or {}
        flat = {}
        defaults = cls.default_policy_payload()
        for section, fields in cls.SECTION_FIELDS.items():
            source = defaults.get(section, {}).copy()
            source.update(payload.get(section, {}) or {})
            for field in fields:
                flat[field] = source.get(field)
        return flat

    @staticmethod
    def _response_safe_value(value):
        if isinstance(value, Decimal):
            return str(value)
        return value

    @classmethod
    def _field_catalog(cls) -> dict:
        return FarmSettings.policy_field_catalog()

    @staticmethod
    def _clear_swallowed_transaction_state() -> None:
        connection = transaction.get_connection()
        if connection.in_atomic_block and connection.needs_rollback:
            transaction.set_rollback(False)

    @classmethod
    def policy_engine_schema_available(cls, *, refresh: bool = False) -> bool:
        alias = connection.alias
        if not refresh and alias in cls._schema_availability_cache:
            return cls._schema_availability_cache[alias]
        try:
            with connection.cursor() as cursor:
                table_names = set(connection.introspection.table_names(cursor))
        except (DatabaseError, OperationalError, ProgrammingError):
            available = False
        else:
            available = cls.POLICY_ENGINE_TABLES.issubset(table_names)
        cls._schema_availability_cache[alias] = available
        return available

    @classmethod
    def _require_policy_engine_schema(cls) -> None:
        if cls.policy_engine_schema_available():
            return
        raise ValidationError(
            "Policy engine schema is not available on the current database. Apply migrations before mutating policy packages."
        )

    @staticmethod
    def _normalize_numeric(field: str, value):
        decimal_fields = {
            "procurement_committee_threshold",
            "local_finance_threshold",
            "sector_review_threshold",
            "sales_tax_percentage",
        }
        integer_fields = {
            "attachment_transient_ttl_days",
            "approved_attachment_archive_after_days",
            "attachment_max_upload_size_mb",
        }
        if field in decimal_fields and value is not None:
            return Decimal(str(value))
        if field in integer_fields and value is not None:
            return int(value)
        return value

    @classmethod
    def json_safe_payload(cls, payload):
        if isinstance(payload, dict):
            return {str(key): cls.json_safe_payload(value) for key, value in payload.items()}
        if isinstance(payload, (list, tuple)):
            return [cls.json_safe_payload(value) for value in payload]
        if isinstance(payload, Decimal):
            return str(payload)
        return payload

    @classmethod
    def validate_policy_payload(cls, payload: dict | None) -> dict:
        payload = cls.json_safe_payload(payload or {})
        flat = cls.flatten_policy_payload(payload)
        flat = {field: cls._normalize_numeric(field, value) for field, value in flat.items()}

        if flat["mode"] == FarmSettings.MODE_SIMPLE:
            if flat["approval_profile"] == FarmSettings.APPROVAL_PROFILE_STRICT_FINANCE:
                raise ValidationError("strict_finance approval profile cannot be activated in SIMPLE mode.")
            if flat["contract_mode"] == FarmSettings.CONTRACT_MODE_FULL_ERP:
                raise ValidationError("full_erp contract mode is forbidden in SIMPLE mode.")
            if flat["fixed_asset_mode"] == FarmSettings.FIXED_ASSET_MODE_FULL_CAPITALIZATION:
                raise ValidationError("full_capitalization fixed asset mode is forbidden in SIMPLE mode.")
            if flat["cost_visibility"] == FarmSettings.COST_VISIBILITY_FULL:
                raise ValidationError("full_amounts cost visibility is forbidden in SIMPLE mode.")
            if flat["treasury_visibility"] == FarmSettings.TREASURY_VISIBILITY_VISIBLE:
                raise ValidationError("visible treasury posture is forbidden in SIMPLE mode.")

        if flat["attachment_enable_cdr"] and flat["attachment_scan_mode"] != FarmSettings.ATTACHMENT_SCAN_MODE_CLAMAV:
            raise ValidationError("CDR can only be enabled when attachment scan mode is clamav.")

        if flat["weekly_remote_review_required"] and not flat["remote_site"]:
            raise ValidationError("weekly remote review requires remote_site=true.")

        if flat["sector_review_threshold"] < flat["local_finance_threshold"]:
            raise ValidationError("sector_review_threshold must be >= local_finance_threshold.")

        if flat["attachment_max_upload_size_mb"] <= 0:
            raise ValidationError("attachment_max_upload_size_mb must be > 0.")

        return flat

    @classmethod
    def _payload_with_flat_patch(cls, *, payload: dict | None, patch: dict | None) -> dict:
        merged = deepcopy(payload or cls.default_policy_payload())
        patch = patch or {}
        for section, fields in cls.SECTION_FIELDS.items():
            section_payload = merged.setdefault(section, {})
            for field in fields:
                if field in patch:
                    section_payload[field] = patch[field]
        return merged

    @classmethod
    def _effective_field_metadata(
        cls,
        *,
        resolved_flat: dict,
        field_sources: dict | None = None,
        field_catalog: dict | None = None,
    ) -> list[dict]:
        field_sources = field_sources or {}
        field_catalog = field_catalog or cls._field_catalog()
        rows = []
        for field in cls.COMPATIBILITY_PROJECTION_FIELDS:
            meta = field_catalog.get(field, {})
            source_meta = field_sources.get(field, {})
            rows.append(
                {
                    "field": field,
                    "label": meta.get("label", field),
                    "section": meta.get("section", ""),
                    "scope": meta.get("scope", ""),
                    "edit_scope": meta.get("edit_scope", ""),
                    "editable": meta.get("edit_scope") != "system-only",
                    "value": cls._response_safe_value(resolved_flat.get(field)),
                    "source": source_meta.get("source", "farm_settings"),
                    "effective_from": source_meta.get("effective_from"),
                    "effective_to": source_meta.get("effective_to"),
                    "reason": source_meta.get("reason", ""),
                }
            )
        return rows

    @staticmethod
    def _enforce_maker_checker(*, actor, maker, action_label: str) -> None:
        if getattr(actor, "is_superuser", False):
            return
        if maker and getattr(actor, "id", None) == getattr(maker, "id", None):
            raise ValidationError(f"Maker-checker violation: creator may not {action_label} the same policy artifact.")

    @classmethod
    def runtime_settings_for_farm(cls, *, farm, settings_obj: FarmSettings | None = None) -> FarmSettings:
        settings_obj = settings_obj or getattr(farm, "settings", None) or FarmSettings.objects.get_or_create(farm=farm)[0]
        resolved = cls.effective_policy_for_farm(farm=farm, settings_obj=settings_obj)
        for field, value in resolved["flat_policy"].items():
            setattr(settings_obj, field, value)
        setattr(settings_obj, "_effective_policy_source", resolved["source"])
        setattr(settings_obj, "_effective_policy_binding_summary", resolved["binding_summary"])
        setattr(settings_obj, "_effective_policy_exception_summary", cls._exception_summary(resolved.get("exception_request")))
        setattr(settings_obj, "_effective_policy_validation_errors", resolved["validation_errors"])
        return settings_obj

    @classmethod
    def _binding_summary(cls, binding: FarmPolicyBinding | None) -> dict | None:
        if binding is None:
            return None
        version = binding.policy_version
        package = getattr(version, "package", None)
        return {
            "binding_id": binding.id,
            "effective_from": binding.effective_from.isoformat() if binding.effective_from else None,
            "effective_to": binding.effective_to.isoformat() if binding.effective_to else None,
            "policy_version_id": version.id,
            "policy_version_label": version.version_label,
            "policy_version_status": version.status,
            "policy_package_id": package.id if package else None,
            "policy_package_name": package.name if package else "",
            "policy_package_slug": package.slug if package else "",
            "source": "policy_binding",
        }

    @staticmethod
    def _exception_summary(exception_request: PolicyExceptionRequest | None) -> dict | None:
        if exception_request is None:
            return None
        return {
            "exception_request_id": exception_request.id,
            "status": exception_request.status,
            "policy_fields": list(exception_request.policy_fields or []),
            "effective_from": exception_request.effective_from.isoformat() if exception_request.effective_from else None,
            "effective_to": exception_request.effective_to.isoformat() if exception_request.effective_to else None,
            "rationale": exception_request.rationale,
            "source": "policy_exception",
        }

    @classmethod
    def active_binding_for_farm(cls, *, farm):
        if not cls.policy_engine_schema_available():
            return None
        now = timezone.now()
        try:
            return (
                FarmPolicyBinding.objects.select_related("policy_version", "policy_version__package")
                .filter(
                    farm=farm,
                    is_active=True,
                    effective_from__lte=now,
                )
                .filter(models.Q(effective_to__isnull=True) | models.Q(effective_to__gt=now))
                .order_by("-effective_from", "-created_at")
                .first()
            )
        except (ProgrammingError, OperationalError):
            cls._clear_swallowed_transaction_state()
            return None

    @classmethod
    def active_exception_for_farm(cls, *, farm):
        if not cls.policy_engine_schema_available():
            return None
        now = timezone.now()
        try:
            return (
                PolicyExceptionRequest.objects.select_related("requested_by", "approved_by", "applied_by")
                .filter(
                    farm=farm,
                    status=PolicyExceptionRequest.STATUS_APPLIED,
                    effective_from__lte=now,
                )
                .filter(models.Q(effective_to__isnull=True) | models.Q(effective_to__gt=now))
                .order_by("-effective_from", "-created_at")
                .first()
            )
        except (ProgrammingError, OperationalError):
            cls._clear_swallowed_transaction_state()
            return None

    @classmethod
    def effective_policy_for_farm(cls, *, farm, settings_obj: FarmSettings | None = None, include_exception: bool = True) -> dict:
        settings_obj = settings_obj or getattr(farm, "settings", None) or FarmSettings.objects.get_or_create(farm=farm)[0]
        binding = cls.active_binding_for_farm(farm=farm)
        validation_errors = []
        exception_request = None
        if binding is not None:
            version = binding.policy_version
            payload = deepcopy(version.payload or {})
            try:
                flat = cls.validate_policy_payload(payload)
            except ValidationError as exc:
                flat = {field: cls._normalize_numeric(field, value) for field, value in cls.flatten_policy_payload(payload).items()}
                validation_errors = list(exc.messages)
                source = "policy_binding_legacy_invalid"
            else:
                source = "policy_binding"
        else:
            payload = cls.policy_payload_from_settings(settings=settings_obj)
            try:
                flat = cls.validate_policy_payload(payload)
            except ValidationError as exc:
                flat = {field: cls._normalize_numeric(field, value) for field, value in cls.flatten_policy_payload(payload).items()}
                validation_errors = list(exc.messages)
                source = "farm_settings_legacy_invalid"
            else:
                source = "farm_settings"

        field_sources = {
            field: {
                "source": source,
                "effective_from": cls._binding_summary(binding).get("effective_from") if binding else None,
                "effective_to": cls._binding_summary(binding).get("effective_to") if binding else None,
                "reason": getattr(binding, "reason", "") if binding else "",
            }
            for field in cls.COMPATIBILITY_PROJECTION_FIELDS
        }

        if include_exception:
            exception_request = cls.active_exception_for_farm(farm=farm)
            if exception_request is not None:
                payload = cls._payload_with_flat_patch(payload=payload, patch=exception_request.requested_patch)
                try:
                    flat = cls.validate_policy_payload(payload)
                except ValidationError as exc:
                    flat = {
                        field: cls._normalize_numeric(field, value)
                        for field, value in cls.flatten_policy_payload(payload).items()
                    }
                    validation_errors.extend(exc.messages)
                    source = f"{source}+exception_legacy_invalid"
                else:
                    source = f"{source}+exception"
                for field in exception_request.requested_patch.keys():
                    field_sources[field] = {
                        "source": "policy_exception",
                        "effective_from": exception_request.effective_from.isoformat() if exception_request.effective_from else None,
                        "effective_to": exception_request.effective_to.isoformat() if exception_request.effective_to else None,
                        "reason": exception_request.rationale,
                    }

        return {
            "source": source,
            "policy_payload": payload,
            "flat_policy": flat,
            "binding": binding,
            "binding_summary": cls._binding_summary(binding),
            "exception_request": exception_request,
            "validation_errors": validation_errors,
            "field_sources": field_sources,
        }

    @classmethod
    def diff_payloads(cls, *, current_payload: dict | None, next_payload: dict | None) -> dict:
        current_flat = {
            field: cls._normalize_numeric(field, value)
            for field, value in cls.flatten_policy_payload(current_payload).items()
        }
        next_flat = {
            field: cls._normalize_numeric(field, value)
            for field, value in cls.flatten_policy_payload(next_payload).items()
        }
        catalog = cls._field_catalog()
        changes = []
        for field in cls.COMPATIBILITY_PROJECTION_FIELDS:
            if current_flat.get(field) == next_flat.get(field):
                continue
            meta = catalog.get(field, {})
            changes.append(
                {
                    "field": field,
                    "label": meta.get("label", field),
                    "section": meta.get("section", ""),
                    "scope": meta.get("scope", ""),
                    "edit_scope": meta.get("edit_scope", ""),
                    "current_value": cls._response_safe_value(current_flat.get(field)),
                    "next_value": cls._response_safe_value(next_flat.get(field)),
                }
            )
        return {
            "changed_fields": [entry["field"] for entry in changes],
            "changed_count": len(changes),
            "changes": changes,
            "current_flat_policy": {
                field: cls._response_safe_value(value) for field, value in current_flat.items()
            },
            "next_flat_policy": {
                field: cls._response_safe_value(value) for field, value in next_flat.items()
            },
        }

    @classmethod
    def _projection_preview(cls, *, farm, next_flat: dict) -> tuple[bool, list[str]]:
        current_settings = getattr(farm, "settings", None) or FarmSettings.objects.get_or_create(farm=farm)[0]
        projected_data = {
            field.name: getattr(current_settings, field.name)
            for field in FarmSettings._meta.fields
            if field.name not in {"id"}
        }
        for field in cls.COMPATIBILITY_PROJECTION_FIELDS:
            projected_data[field] = next_flat.get(field)
        preview = FarmSettings(**projected_data)
        preview.farm = farm
        try:
            preview.clean()
        except ValidationError as exc:
            return False, list(exc.messages)
        return True, []

    @classmethod
    def activation_eligibility(cls, *, farm, policy_version: PolicyVersion) -> dict:
        current_settings = getattr(farm, "settings", None) or FarmSettings.objects.get_or_create(farm=farm)[0]
        current = cls.effective_policy_for_farm(farm=farm, settings_obj=current_settings)
        simulation = cls.simulate_activation(farm=farm, policy_version=policy_version)
        diff = cls.diff_payloads(
            current_payload=current["policy_payload"],
            next_payload=policy_version.payload,
        )
        blockers = []
        warnings = []

        if not getattr(policy_version.package, "is_active", True):
            blockers.append("The selected policy package is inactive.")
        if policy_version.status != PolicyVersion.STATUS_APPROVED:
            blockers.append("Only approved policy versions may be activated.")

        try:
            next_flat = cls.validate_policy_payload(policy_version.payload)
        except ValidationError as exc:
            next_flat = {
                field: cls._normalize_numeric(field, value)
                for field, value in cls.flatten_policy_payload(policy_version.payload).items()
            }
            blockers.extend(exc.messages)
        else:
            projection_ok, projection_blockers = cls._projection_preview(farm=farm, next_flat=next_flat)
            if not projection_ok:
                blockers.extend(projection_blockers)

        if current["binding_summary"] is not None:
            warnings.append(cls.DEFAULT_ELIGIBILITY_WARNINGS["policy_binding_replace"])
        if simulation["from_mode"] != simulation["to_mode"]:
            warnings.append(cls.DEFAULT_ELIGIBILITY_WARNINGS["strict_mode_transition"])
        if next_flat.get("weekly_remote_review_required"):
            warnings.append(cls.DEFAULT_ELIGIBILITY_WARNINGS["remote_review_enforced"])
        if next_flat.get("mode") == FarmSettings.MODE_STRICT and next_flat.get("attachment_require_clean_scan_for_strict"):
            warnings.append(cls.DEFAULT_ELIGIBILITY_WARNINGS["attachment_clean_scan"])

        return {
            "eligible": len(blockers) == 0,
            "farm_id": farm.id,
            "policy_version_id": policy_version.id,
            "current_source": current["source"],
            "current_binding": current["binding_summary"],
            "simulation": simulation,
            "diff": diff,
            "blockers": blockers,
            "warnings": warnings,
            "current_validation_errors": current["validation_errors"],
        }

    @classmethod
    def effective_policy_summary_for_farm(cls, *, farm, settings_obj: FarmSettings | None = None) -> dict:
        settings_obj = settings_obj or getattr(farm, "settings", None) or FarmSettings.objects.get_or_create(farm=farm)[0]
        resolved = cls.effective_policy_for_farm(farm=farm, settings_obj=settings_obj)
        return {
            "farm_id": farm.id,
            "source": resolved["source"],
            "binding_summary": resolved["binding_summary"],
            "exception_summary": cls._exception_summary(resolved.get("exception_request")),
            "policy_payload": resolved["policy_payload"],
            "flat_policy": {
                field: cls._response_safe_value(value)
                for field, value in resolved["flat_policy"].items()
            },
            "validation_errors": resolved["validation_errors"],
            "field_catalog": cls._field_catalog(),
            "effective_fields": cls._effective_field_metadata(
                resolved_flat=resolved["flat_policy"],
                field_sources=resolved.get("field_sources") or {},
                field_catalog=cls._field_catalog(),
            ),
        }

    @classmethod
    def package_usage_snapshot(cls) -> dict:
        if not cls.policy_engine_schema_available():
            return {
                "generated_at": timezone.now().isoformat(),
                "packages": [],
                "summary": {"packages": 0, "active_bindings": 0, "expired_bindings": 0, "farms_with_exceptions": 0},
            }
        packages = []
        farms_with_exceptions = set(
            PolicyExceptionRequest.objects.filter(
                status__in=[
                    PolicyExceptionRequest.STATUS_DRAFT,
                    PolicyExceptionRequest.STATUS_PENDING,
                    PolicyExceptionRequest.STATUS_APPROVED,
                    PolicyExceptionRequest.STATUS_APPLIED,
                ]
            ).values_list("farm_id", flat=True)
        )
        for package in PolicyPackage.objects.all().order_by("name"):
            versions = list(package.versions.all())
            version_ids = [version.id for version in versions]
            bindings = FarmPolicyBinding.objects.filter(policy_version_id__in=version_ids)
            active_bindings = bindings.filter(is_active=True).count()
            expired_bindings = bindings.exclude(is_active=True).count()
            farm_ids = set(bindings.values_list("farm_id", flat=True))
            package_exception_farm_ids = set(
                PolicyExceptionRequest.objects.filter(
                    farm_id__in=farm_ids,
                    status__in=[
                        PolicyExceptionRequest.STATUS_DRAFT,
                        PolicyExceptionRequest.STATUS_PENDING,
                        PolicyExceptionRequest.STATUS_APPROVED,
                        PolicyExceptionRequest.STATUS_APPLIED,
                    ],
                ).values_list("farm_id", flat=True)
            )
            packages.append(
                {
                    "package_id": package.id,
                    "package_name": package.name,
                    "package_slug": package.slug,
                    "is_active": package.is_active,
                    "versions_count": len(versions),
                    "approved_versions_count": sum(1 for version in versions if version.status == PolicyVersion.STATUS_APPROVED),
                    "farm_count": len(farm_ids),
                    "active_bindings": active_bindings,
                    "expired_bindings": expired_bindings,
                    "exception_farm_count": len(package_exception_farm_ids),
                }
            )
        return {
            "generated_at": timezone.now().isoformat(),
            "packages": packages,
            "summary": {
                "packages": len(packages),
                "active_bindings": sum(item["active_bindings"] for item in packages),
                "expired_bindings": sum(item["expired_bindings"] for item in packages),
                "farms_with_exceptions": len(farms_with_exceptions),
            },
        }

    @classmethod
    def activation_timeline_snapshot(cls) -> dict:
        if not cls.policy_engine_schema_available():
            return {
                "generated_at": timezone.now().isoformat(),
                "counts_by_status": {},
                "maker_checker": {"same_actor_pairs": 0, "split_actor_pairs": 0},
                "latest_requests": [],
                "latest_events": [],
            }
        requests = list(
            PolicyActivationRequest.objects.select_related("farm", "policy_version", "policy_version__package", "requested_by", "approved_by")
            .order_by("-created_at")[:10]
        )
        events = list(
            PolicyActivationEvent.objects.select_related("farm", "policy_version", "policy_version__package", "actor")
            .order_by("-created_at")[:10]
        )
        counts_by_status = dict(
            Counter(PolicyActivationRequest.objects.values_list("status", flat=True))
        )
        same_actor_pairs = 0
        split_actor_pairs = 0
        for request in PolicyActivationRequest.objects.exclude(requested_by__isnull=True):
            if request.approved_by_id:
                if request.requested_by_id == request.approved_by_id:
                    same_actor_pairs += 1
                else:
                    split_actor_pairs += 1
        return {
            "generated_at": timezone.now().isoformat(),
            "counts_by_status": counts_by_status,
            "maker_checker": {
                "same_actor_pairs": same_actor_pairs,
                "split_actor_pairs": split_actor_pairs,
            },
            "latest_requests": [
                {
                    "id": request.id,
                    "farm_id": request.farm_id,
                    "farm_name": request.farm.name,
                    "package_name": request.policy_version.package.name,
                    "version_label": request.policy_version.version_label,
                    "status": request.status,
                    "requested_by": getattr(request.requested_by, "username", ""),
                    "approved_by": getattr(request.approved_by, "username", ""),
                    "created_at": request.created_at.isoformat(),
                }
                for request in requests
            ],
            "latest_events": [
                {
                    "id": event.id,
                    "farm_id": event.farm_id,
                    "farm_name": event.farm.name,
                    "package_name": event.policy_version.package.name,
                    "version_label": event.policy_version.version_label,
                    "action": event.action,
                    "actor_username": getattr(event.actor, "username", ""),
                    "created_at": event.created_at.isoformat(),
                }
                for event in events
            ],
        }

    @classmethod
    def exception_pressure_snapshot(cls) -> dict:
        if not cls.policy_engine_schema_available():
            return {
                "generated_at": timezone.now().isoformat(),
                "open_by_farm": [],
                "open_by_field_family": {},
                "forbidden_field_rejections": 0,
                "expiring_soon": [],
            }
        open_statuses = [
            PolicyExceptionRequest.STATUS_DRAFT,
            PolicyExceptionRequest.STATUS_PENDING,
            PolicyExceptionRequest.STATUS_APPROVED,
            PolicyExceptionRequest.STATUS_APPLIED,
        ]
        open_requests = list(
            PolicyExceptionRequest.objects.select_related("farm")
            .filter(status__in=open_statuses)
            .order_by("-created_at")
        )
        field_family_counts = Counter()
        open_by_farm = defaultdict(lambda: {"farm_id": None, "farm_name": "", "count": 0, "fields": Counter()})
        expiring_soon = []
        now = timezone.now()
        for request in open_requests:
            bucket = open_by_farm[request.farm_id]
            bucket["farm_id"] = request.farm_id
            bucket["farm_name"] = request.farm.name
            bucket["count"] += 1
            for field in request.policy_fields or []:
                family = cls._field_catalog().get(field, {}).get("section", "unclassified")
                field_family_counts[family] += 1
                bucket["fields"][field] += 1
            if request.effective_to and request.effective_to <= now + timedelta(days=7):
                expiring_soon.append(
                    {
                        "id": request.id,
                        "farm_id": request.farm_id,
                        "farm_name": request.farm.name,
                        "status": request.status,
                        "effective_to": request.effective_to.isoformat(),
                        "policy_fields": list(request.policy_fields or []),
                    }
                )
        forbidden_field_rejections = 0
        for request in PolicyExceptionRequest.objects.filter(status=PolicyExceptionRequest.STATUS_REJECTED):
            summary = request.simulate_summary or {}
            messages = summary.get("messages") or summary.get("blockers") or []
            if any("forbidden" in str(message).lower() or "not eligible" in str(message).lower() for message in messages):
                forbidden_field_rejections += 1
        return {
            "generated_at": timezone.now().isoformat(),
            "open_by_farm": [
                {
                    "farm_id": row["farm_id"],
                    "farm_name": row["farm_name"],
                    "count": row["count"],
                    "fields": dict(row["fields"]),
                }
                for row in sorted(open_by_farm.values(), key=lambda item: (-item["count"], item["farm_name"]))
            ],
            "open_by_field_family": dict(field_family_counts),
            "forbidden_field_rejections": forbidden_field_rejections,
            "expiring_soon": expiring_soon[:10],
        }

    @classmethod
    def diff_against_farm_settings_patch(cls, *, farm, patch_payload: dict, settings_obj: FarmSettings | None = None) -> dict:
        settings_obj = settings_obj or getattr(farm, "settings", None) or FarmSettings.objects.get_or_create(farm=farm)[0]
        current_payload = cls.policy_payload_from_settings(settings=settings_obj)
        next_payload = deepcopy(current_payload)
        for section, fields in cls.SECTION_FIELDS.items():
            target = next_payload.setdefault(section, {})
            for field in fields:
                if field in patch_payload:
                    target[field] = patch_payload[field]
        diff = cls.diff_payloads(current_payload=current_payload, next_payload=next_payload)
        blockers = []
        try:
            next_flat = cls.validate_policy_payload(next_payload)
        except ValidationError as exc:
            blockers.extend(exc.messages)
        else:
            projection_ok, projection_blockers = cls._projection_preview(farm=farm, next_flat=next_flat)
            if not projection_ok:
                blockers.extend(projection_blockers)
        return {
            **diff,
            "eligible": len(blockers) == 0,
            "blockers": blockers,
        }

    @classmethod
    def diff_policy_version(
        cls,
        *,
        policy_version: PolicyVersion,
        compare_to_version: PolicyVersion | None = None,
        farm=None,
    ) -> dict:
        comparison_mode = "version_to_version" if compare_to_version is not None else "version_to_farm"
        if compare_to_version is not None:
            compare_payload = compare_to_version.payload
            compare_summary = {
                "type": "policy_version",
                "policy_version_id": compare_to_version.id,
                "policy_package_id": compare_to_version.package_id,
                "policy_package_name": compare_to_version.package.name,
                "policy_version_label": compare_to_version.version_label,
            }
        elif farm is not None:
            current = cls.effective_policy_for_farm(farm=farm)
            compare_payload = current["policy_payload"]
            compare_summary = {
                "type": "farm_effective_policy",
                "farm_id": farm.id,
                "source": current["source"],
                "binding_summary": current["binding_summary"],
                "exception_summary": cls._exception_summary(current.get("exception_request")),
            }
        else:
            raise ValidationError("Policy version diff requires either compare_to_version or farm.")

        diff = cls.diff_payloads(
            current_payload=compare_payload,
            next_payload=policy_version.payload,
        )
        return {
            "comparison_mode": comparison_mode,
            "policy_version_id": policy_version.id,
            "compare_to": compare_summary,
            "changed_fields": diff["changed_fields"],
            "changed_count": diff["changed_count"],
            "diff": diff,
        }

    @classmethod
    def policy_divergence(cls, *, settings_obj: FarmSettings, global_settings) -> dict:
        farm_strict = settings_obj.mode == FarmSettings.MODE_STRICT
        global_strict = bool(getattr(global_settings, "strict_erp_mode", False))
        detected = global_strict and not farm_strict
        return {
            "detected": detected,
            "farm_mode": settings_obj.mode,
            "legacy_global_strict_erp_mode": global_strict,
            "warning": (
                "Legacy SystemSettings.strict_erp_mode diverges from FarmSettings.mode. "
                "FarmSettings.mode remains the canonical runtime contract."
            ) if detected else "",
        }

    @classmethod
    def validate_exception_patch(
        cls,
        *,
        farm,
        requested_patch: dict,
        effective_from,
        effective_to,
    ) -> dict:
        patch = cls.json_safe_payload(requested_patch or {})
        patch_fields = set(patch.keys())
        if not patch_fields:
            raise ValidationError("Policy exception patch may not be empty.")
        illegal_fields = sorted(patch_fields - cls.EXCEPTION_ELIGIBLE_FIELDS)
        if illegal_fields:
            raise ValidationError(
                f"Policy exceptions may not override these fields: {', '.join(illegal_fields)}."
            )
        if effective_to is None:
            raise ValidationError("Policy exceptions require an effective_to window.")
        if effective_to <= effective_from:
            raise ValidationError("effective_to must be later than effective_from.")

        current = cls.effective_policy_for_farm(farm=farm, include_exception=False)
        next_payload = cls._payload_with_flat_patch(
            payload=current["policy_payload"],
            patch=patch,
        )
        next_flat = cls.validate_policy_payload(next_payload)
        projection_ok, projection_blockers = cls._projection_preview(farm=farm, next_flat=next_flat)
        if not projection_ok:
            raise ValidationError(projection_blockers)

        return {
            "policy_fields": sorted(patch_fields),
            "diff": cls.diff_payloads(
                current_payload=current["policy_payload"],
                next_payload=next_payload,
            ),
            "current_source": current["source"],
            "eligible": True,
            "blockers": [],
            "warnings": [
                "Approved farm exceptions remain temporary and farm-scoped only.",
            ],
            "effective_from": effective_from.isoformat() if effective_from else None,
            "effective_to": effective_to.isoformat() if effective_to else None,
        }

    @classmethod
    @transaction.atomic
    def create_package(cls, *, actor, **validated_data) -> PolicyPackage:
        cls._require_sector_central_authority(actor)
        cls._require_policy_engine_schema()
        return PolicyPackage.objects.create(created_by=actor, updated_by=actor, **validated_data)

    @classmethod
    @transaction.atomic
    def update_package(cls, *, actor, instance: PolicyPackage, **validated_data) -> PolicyPackage:
        cls._require_sector_central_authority(actor)
        cls._require_policy_engine_schema()
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.updated_by = actor
        instance.full_clean()
        instance.save()
        return instance

    @classmethod
    @transaction.atomic
    def create_version(cls, *, actor, package: PolicyPackage, version_label: str, payload: dict) -> PolicyVersion:
        cls._require_sector_central_authority(actor)
        cls._require_policy_engine_schema()
        payload = cls.json_safe_payload(payload)
        cls.validate_policy_payload(payload)
        return PolicyVersion.objects.create(
            package=package,
            version_label=version_label,
            payload=payload,
            created_by=actor,
            updated_by=actor,
        )

    @classmethod
    @transaction.atomic
    def update_version(cls, *, actor, instance: PolicyVersion, **validated_data) -> PolicyVersion:
        cls._require_sector_central_authority(actor)
        cls._require_policy_engine_schema()
        if instance.status != PolicyVersion.STATUS_DRAFT:
            raise ValidationError("Approved or retired policy versions are immutable.")
        payload = cls.json_safe_payload(validated_data.get("payload", instance.payload))
        cls.validate_policy_payload(payload)
        validated_data["payload"] = payload
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.updated_by = actor
        instance.full_clean()
        instance.save()
        return instance

    @classmethod
    @transaction.atomic
    def approve_version(cls, *, actor, instance: PolicyVersion) -> PolicyVersion:
        cls._require_sector_central_authority(actor)
        cls._require_policy_engine_schema()
        cls._enforce_maker_checker(actor=actor, maker=instance.created_by, action_label="approve")
        cls.validate_policy_payload(instance.payload)
        instance.status = PolicyVersion.STATUS_APPROVED
        instance.approved_by = actor
        instance.approved_at = timezone.now()
        instance.updated_by = actor
        instance.save(update_fields=["status", "approved_by", "approved_at", "updated_by", "updated_at"])
        return instance

    @classmethod
    @transaction.atomic
    def retire_version(cls, *, actor, instance: PolicyVersion) -> PolicyVersion:
        cls._require_sector_central_authority(actor)
        cls._require_policy_engine_schema()
        if instance.status != PolicyVersion.STATUS_APPROVED:
            raise ValidationError("Only approved policy versions may be retired.")
        instance.status = PolicyVersion.STATUS_RETIRED
        instance.updated_by = actor
        instance.save(update_fields=["status", "updated_by", "updated_at"])
        return instance

    @classmethod
    def simulate_activation(cls, *, farm, policy_version: PolicyVersion) -> dict:
        settings_obj = getattr(farm, "settings", None) or FarmSettings.objects.get_or_create(farm=farm)[0]
        current_flat = cls.policy_payload_from_settings(settings=settings_obj)
        next_flat = cls.flatten_policy_payload(policy_version.payload)
        changed = []
        current_flat_values = cls.flatten_policy_payload(current_flat)
        for field in cls.COMPATIBILITY_PROJECTION_FIELDS:
            if current_flat_values.get(field) != next_flat.get(field):
                changed.append(field)
        return {
            "farm_id": farm.id,
            "policy_version_id": policy_version.id,
            "changed_fields": changed,
            "changed_count": len(changed),
            "from_mode": settings_obj.mode,
            "to_mode": next_flat.get("mode"),
        }

    @classmethod
    @transaction.atomic
    def create_activation_request(cls, *, actor, farm, policy_version: PolicyVersion, rationale: str = "", effective_from=None) -> PolicyActivationRequest:
        cls._require_sector_central_authority(actor)
        cls._require_policy_engine_schema()
        if policy_version.status != PolicyVersion.STATUS_APPROVED:
            raise ValidationError("Only approved policy versions may enter activation.")
        eligibility = cls.activation_eligibility(farm=farm, policy_version=policy_version)
        if not eligibility["eligible"]:
            raise ValidationError(eligibility["blockers"])
        effective_from = effective_from or timezone.now()
        duplicate = PolicyActivationRequest.objects.filter(
            farm=farm,
            policy_version=policy_version,
            effective_from=effective_from,
            status__in={
                PolicyActivationRequest.STATUS_DRAFT,
                PolicyActivationRequest.STATUS_PENDING,
                PolicyActivationRequest.STATUS_APPROVED,
            },
        ).exists()
        if duplicate:
            raise ValidationError("A pending activation request already exists for this farm, policy version, and effective date.")
        request_obj = PolicyActivationRequest.objects.create(
            farm=farm,
            policy_version=policy_version,
            rationale=rationale,
            effective_from=effective_from,
            requested_by=actor,
            simulate_summary=eligibility,
        )
        cls._record_event(
            activation_request=request_obj,
            farm=farm,
            policy_version=policy_version,
            action=PolicyActivationEvent.ACTION_CREATED,
            actor=actor,
            note="Policy activation request created.",
            metadata=request_obj.simulate_summary,
        )
        return request_obj

    @classmethod
    @transaction.atomic
    def submit_activation_request(cls, *, actor, instance: PolicyActivationRequest) -> PolicyActivationRequest:
        cls._require_sector_central_authority(actor)
        cls._require_policy_engine_schema()
        if instance.status != PolicyActivationRequest.STATUS_DRAFT:
            raise ValidationError("Only draft requests can be submitted.")
        eligibility = cls.activation_eligibility(farm=instance.farm, policy_version=instance.policy_version)
        if not eligibility["eligible"]:
            raise ValidationError(eligibility["blockers"])
        instance.status = PolicyActivationRequest.STATUS_PENDING
        instance.simulate_summary = eligibility
        instance.save(update_fields=["status", "simulate_summary", "updated_at"])
        cls._record_event(
            activation_request=instance,
            farm=instance.farm,
            policy_version=instance.policy_version,
            action=PolicyActivationEvent.ACTION_SUBMITTED,
            actor=actor,
            note="Policy activation request submitted.",
        )
        return instance

    @classmethod
    @transaction.atomic
    def approve_activation_request(cls, *, actor, instance: PolicyActivationRequest) -> PolicyActivationRequest:
        cls._require_sector_central_authority(actor)
        cls._require_policy_engine_schema()
        if instance.status not in {PolicyActivationRequest.STATUS_DRAFT, PolicyActivationRequest.STATUS_PENDING}:
            raise ValidationError("Only draft or pending requests can be approved.")
        cls._enforce_maker_checker(actor=actor, maker=instance.requested_by, action_label="approve")
        eligibility = cls.activation_eligibility(farm=instance.farm, policy_version=instance.policy_version)
        if not eligibility["eligible"]:
            raise ValidationError(eligibility["blockers"])
        instance.status = PolicyActivationRequest.STATUS_APPROVED
        instance.approved_by = actor
        instance.simulate_summary = eligibility
        instance.save(update_fields=["status", "approved_by", "simulate_summary", "updated_at"])
        cls._record_event(
            activation_request=instance,
            farm=instance.farm,
            policy_version=instance.policy_version,
            action=PolicyActivationEvent.ACTION_APPROVED,
            actor=actor,
            note="Policy activation request approved.",
        )
        return instance

    @classmethod
    @transaction.atomic
    def reject_activation_request(cls, *, actor, instance: PolicyActivationRequest, note: str = "") -> PolicyActivationRequest:
        cls._require_sector_central_authority(actor)
        cls._require_policy_engine_schema()
        if instance.status == PolicyActivationRequest.STATUS_APPLIED:
            raise ValidationError("Applied requests cannot be rejected.")
        instance.status = PolicyActivationRequest.STATUS_REJECTED
        instance.rejected_by = actor
        instance.save(update_fields=["status", "rejected_by", "updated_at"])
        cls._record_event(
            activation_request=instance,
            farm=instance.farm,
            policy_version=instance.policy_version,
            action=PolicyActivationEvent.ACTION_REJECTED,
            actor=actor,
            note=note or "Policy activation request rejected.",
        )
        return instance

    @classmethod
    @transaction.atomic
    def project_version_to_farm_settings(cls, *, farm, policy_version: PolicyVersion, actor=None) -> FarmSettings:
        if policy_version.status != PolicyVersion.STATUS_APPROVED:
            raise ValidationError("Only approved policy versions can be projected.")
        flat = cls.validate_policy_payload(policy_version.payload)
        settings_obj, _ = FarmSettings.objects.get_or_create(farm=farm)
        for field in cls.COMPATIBILITY_PROJECTION_FIELDS:
            setattr(settings_obj, field, flat[field])
        settings_obj.full_clean()
        settings_obj.save()
        return settings_obj

    @classmethod
    @transaction.atomic
    def apply_activation_request(cls, *, actor, instance: PolicyActivationRequest) -> PolicyActivationRequest:
        cls._require_sector_central_authority(actor)
        cls._require_policy_engine_schema()
        if instance.status != PolicyActivationRequest.STATUS_APPROVED:
            raise ValidationError("Only approved requests can be applied.")
        cls._enforce_maker_checker(actor=actor, maker=instance.requested_by, action_label="apply")
        eligibility = cls.activation_eligibility(farm=instance.farm, policy_version=instance.policy_version)
        if not eligibility["eligible"]:
            raise ValidationError(eligibility["blockers"])

        now = timezone.now()
        prior_bindings = FarmPolicyBinding.objects.select_for_update().filter(
            farm=instance.farm,
            is_active=True,
        )
        for binding in prior_bindings:
            binding.is_active = False
            if binding.effective_to is None or binding.effective_to > instance.effective_from:
                binding.effective_to = instance.effective_from
            binding.save(update_fields=["is_active", "effective_to", "updated_at"])

        binding = FarmPolicyBinding.objects.create(
            farm=instance.farm,
            policy_version=instance.policy_version,
            effective_from=instance.effective_from,
            is_active=True,
            reason=instance.rationale,
            created_by=instance.requested_by,
            approved_by=actor,
        )
        cls.project_version_to_farm_settings(farm=instance.farm, policy_version=instance.policy_version, actor=actor)
        instance.status = PolicyActivationRequest.STATUS_APPLIED
        instance.applied_binding = binding
        instance.save(update_fields=["status", "applied_binding", "updated_at"])
        cls._record_event(
            activation_request=instance,
            farm=instance.farm,
            policy_version=instance.policy_version,
            action=PolicyActivationEvent.ACTION_APPLIED,
            actor=actor,
            note="Policy activation request applied.",
            metadata={"binding_id": binding.id, "applied_at": now.isoformat()},
        )
        return instance

    @classmethod
    @transaction.atomic
    def create_exception_request(
        cls,
        *,
        actor,
        farm,
        requested_patch: dict,
        rationale: str = "",
        effective_from=None,
        effective_to=None,
    ) -> PolicyExceptionRequest:
        cls._require_sector_central_authority(actor)
        cls._require_policy_engine_schema()
        effective_from = effective_from or timezone.now()
        summary = cls.validate_exception_patch(
            farm=farm,
            requested_patch=requested_patch,
            effective_from=effective_from,
            effective_to=effective_to,
        )
        request_obj = PolicyExceptionRequest.objects.create(
            farm=farm,
            policy_fields=summary["policy_fields"],
            requested_patch=cls.json_safe_payload(requested_patch),
            rationale=rationale,
            effective_from=effective_from,
            effective_to=effective_to,
            requested_by=actor,
            simulate_summary=summary,
        )
        cls._record_exception_event(
            exception_request=request_obj,
            farm=farm,
            action=PolicyExceptionEvent.ACTION_CREATED,
            actor=actor,
            note="Policy exception request created.",
            metadata=summary,
        )
        return request_obj

    @classmethod
    @transaction.atomic
    def submit_exception_request(cls, *, actor, instance: PolicyExceptionRequest) -> PolicyExceptionRequest:
        cls._require_sector_central_authority(actor)
        cls._require_policy_engine_schema()
        if instance.status != PolicyExceptionRequest.STATUS_DRAFT:
            raise ValidationError("Only draft exception requests can be submitted.")
        summary = cls.validate_exception_patch(
            farm=instance.farm,
            requested_patch=instance.requested_patch,
            effective_from=instance.effective_from,
            effective_to=instance.effective_to,
        )
        instance.status = PolicyExceptionRequest.STATUS_PENDING
        instance.simulate_summary = summary
        instance.save(update_fields=["status", "simulate_summary", "updated_at"])
        cls._record_exception_event(
            exception_request=instance,
            farm=instance.farm,
            action=PolicyExceptionEvent.ACTION_SUBMITTED,
            actor=actor,
            note="Policy exception request submitted.",
        )
        return instance

    @classmethod
    @transaction.atomic
    def approve_exception_request(cls, *, actor, instance: PolicyExceptionRequest) -> PolicyExceptionRequest:
        cls._require_sector_central_authority(actor)
        cls._require_policy_engine_schema()
        if instance.status not in {PolicyExceptionRequest.STATUS_DRAFT, PolicyExceptionRequest.STATUS_PENDING}:
            raise ValidationError("Only draft or pending exception requests can be approved.")
        cls._enforce_maker_checker(actor=actor, maker=instance.requested_by, action_label="approve")
        summary = cls.validate_exception_patch(
            farm=instance.farm,
            requested_patch=instance.requested_patch,
            effective_from=instance.effective_from,
            effective_to=instance.effective_to,
        )
        instance.status = PolicyExceptionRequest.STATUS_APPROVED
        instance.approved_by = actor
        instance.simulate_summary = summary
        instance.save(update_fields=["status", "approved_by", "simulate_summary", "updated_at"])
        cls._record_exception_event(
            exception_request=instance,
            farm=instance.farm,
            action=PolicyExceptionEvent.ACTION_APPROVED,
            actor=actor,
            note="Policy exception request approved.",
        )
        return instance

    @classmethod
    @transaction.atomic
    def reject_exception_request(cls, *, actor, instance: PolicyExceptionRequest, note: str = "") -> PolicyExceptionRequest:
        cls._require_sector_central_authority(actor)
        cls._require_policy_engine_schema()
        if instance.status == PolicyExceptionRequest.STATUS_APPLIED:
            raise ValidationError("Applied exception requests cannot be rejected.")
        instance.status = PolicyExceptionRequest.STATUS_REJECTED
        instance.rejected_by = actor
        instance.save(update_fields=["status", "rejected_by", "updated_at"])
        cls._record_exception_event(
            exception_request=instance,
            farm=instance.farm,
            action=PolicyExceptionEvent.ACTION_REJECTED,
            actor=actor,
            note=note or "Policy exception request rejected.",
        )
        return instance

    @classmethod
    @transaction.atomic
    def apply_exception_request(cls, *, actor, instance: PolicyExceptionRequest) -> PolicyExceptionRequest:
        cls._require_sector_central_authority(actor)
        cls._require_policy_engine_schema()
        if instance.status != PolicyExceptionRequest.STATUS_APPROVED:
            raise ValidationError("Only approved exception requests can be applied.")
        cls._enforce_maker_checker(actor=actor, maker=instance.requested_by, action_label="apply")
        if instance.effective_to and instance.effective_to <= timezone.now():
            raise ValidationError("Expired exception requests cannot be applied.")
        cls.validate_exception_patch(
            farm=instance.farm,
            requested_patch=instance.requested_patch,
            effective_from=instance.effective_from,
            effective_to=instance.effective_to,
        )
        overlapping = PolicyExceptionRequest.objects.select_for_update().filter(
            farm=instance.farm,
            status=PolicyExceptionRequest.STATUS_APPLIED,
        ).exclude(pk=instance.pk)
        for row in overlapping:
            row.status = PolicyExceptionRequest.STATUS_EXPIRED
            row.save(update_fields=["status", "updated_at"])
            cls._record_exception_event(
                exception_request=row,
                farm=row.farm,
                action=PolicyExceptionEvent.ACTION_EXPIRED,
                actor=actor,
                note="Policy exception expired due to replacement.",
            )
        instance.status = PolicyExceptionRequest.STATUS_APPLIED
        instance.applied_by = actor
        instance.save(update_fields=["status", "applied_by", "updated_at"])
        cls._record_exception_event(
            exception_request=instance,
            farm=instance.farm,
            action=PolicyExceptionEvent.ACTION_APPLIED,
            actor=actor,
            note="Policy exception request applied.",
        )
        return instance

    @staticmethod
    def _record_event(*, activation_request, farm, policy_version, action: str, actor, note: str = "", metadata: dict | None = None):
        PolicyActivationEvent.objects.create(
            activation_request=activation_request,
            farm=farm,
            policy_version=policy_version,
            action=action,
            actor=actor,
            note=(note or "")[:255],
            metadata=metadata or {},
        )
        logger.info(
            f'policy.activation.{action}',
            extra={
                'correlation_id': (metadata or {}).get('correlation_id') or f'policy-activation-{activation_request.id}',
                'farm_id': getattr(farm, 'id', None),
                'policy_version_id': getattr(policy_version, 'id', None),
                'activation_request_id': getattr(activation_request, 'id', None),
                'actor_id': getattr(actor, 'id', None),
                'action': action,
            },
        )

    @staticmethod
    def _record_exception_event(*, exception_request, farm, action: str, actor, note: str = "", metadata: dict | None = None):
        PolicyExceptionEvent.objects.create(
            exception_request=exception_request,
            farm=farm,
            action=action,
            actor=actor,
            note=(note or "")[:255],
            metadata=metadata or {},
        )
        logger.info(
            f'policy.exception.{action}',
            extra={
                'correlation_id': (metadata or {}).get('correlation_id') or f'policy-exception-{exception_request.id}',
                'farm_id': getattr(farm, 'id', None),
                'exception_request_id': getattr(exception_request, 'id', None),
                'actor_id': getattr(actor, 'id', None),
                'action': action,
            },
        )
