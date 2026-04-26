from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from unittest import mock
from datetime import timedelta

from smart_agri.core.models import (
    Farm,
    FarmPolicyBinding,
    PolicyActivationEvent,
    PolicyExceptionEvent,
    PolicyExceptionRequest,
    PolicyPackage,
    PolicyVersion,
)
from smart_agri.core.models.settings import FarmSettings
from smart_agri.core.services.policy_engine_service import PolicyEngineService


class PolicyEngineServiceTests(TestCase):
    def setUp(self):
        self.actor = User.objects.create_user(
            username="sector_policy_owner",
            password="pass",
            is_staff=True,
            is_superuser=True,
        )
        self.farm = Farm.objects.create(name="Policy Engine Farm", slug="policy-engine-farm", region="A")
        self.settings = FarmSettings.objects.create(farm=self.farm)

    def test_validate_policy_payload_rejects_simple_full_erp_invariants(self):
        payload = PolicyEngineService.default_policy_payload()
        payload["dual_mode_policy"]["mode"] = FarmSettings.MODE_SIMPLE
        payload["dual_mode_policy"]["contract_mode"] = FarmSettings.CONTRACT_MODE_FULL_ERP

        with self.assertRaises(ValidationError):
            PolicyEngineService.validate_policy_payload(payload)

    def test_effective_policy_defaults_to_farm_settings_when_no_binding(self):
        resolved = PolicyEngineService.effective_policy_for_farm(farm=self.farm, settings_obj=self.settings)

        self.assertEqual(resolved["source"], "farm_settings")
        self.assertIsNone(resolved["binding"])
        self.assertEqual(
            resolved["policy_payload"]["dual_mode_policy"]["mode"],
            FarmSettings.MODE_SIMPLE,
        )

    def test_activation_request_apply_projects_approved_policy_to_farm_settings(self):
        package = PolicyEngineService.create_package(
            actor=self.actor,
            name="Central Strict Package",
            slug="central-strict-package",
            description="Central policy package for strict governance.",
        )
        payload = PolicyEngineService.default_policy_payload()
        payload["dual_mode_policy"]["mode"] = FarmSettings.MODE_STRICT
        payload["dual_mode_policy"]["approval_profile"] = FarmSettings.APPROVAL_PROFILE_TIERED
        payload["dual_mode_policy"]["contract_mode"] = FarmSettings.CONTRACT_MODE_OPERATIONAL_ONLY
        payload["dual_mode_policy"]["treasury_visibility"] = FarmSettings.TREASURY_VISIBILITY_FINANCE_ONLY
        payload["dual_mode_policy"]["fixed_asset_mode"] = FarmSettings.FIXED_ASSET_MODE_TRACKING_ONLY
        payload["attachment_policy"]["attachment_scan_mode"] = FarmSettings.ATTACHMENT_SCAN_MODE_CLAMAV
        payload["attachment_policy"]["attachment_require_clean_scan_for_strict"] = True
        payload["remote_review_policy"]["remote_site"] = True
        payload["remote_review_policy"]["weekly_remote_review_required"] = True

        version = PolicyEngineService.create_version(
            actor=self.actor,
            package=package,
            version_label="v1",
            payload=payload,
        )
        PolicyEngineService.approve_version(actor=self.actor, instance=version)
        request_obj = PolicyEngineService.create_activation_request(
            actor=self.actor,
            farm=self.farm,
            policy_version=version,
            rationale="Enable central strict policy.",
        )
        PolicyEngineService.submit_activation_request(actor=self.actor, instance=request_obj)
        PolicyEngineService.approve_activation_request(actor=self.actor, instance=request_obj)
        PolicyEngineService.apply_activation_request(actor=self.actor, instance=request_obj)

        self.settings.refresh_from_db()
        request_obj.refresh_from_db()

        self.assertEqual(self.settings.mode, FarmSettings.MODE_STRICT)
        self.assertEqual(self.settings.attachment_scan_mode, FarmSettings.ATTACHMENT_SCAN_MODE_CLAMAV)
        self.assertTrue(self.settings.remote_site)
        self.assertTrue(self.settings.weekly_remote_review_required)
        self.assertEqual(request_obj.status, request_obj.STATUS_APPLIED)
        self.assertIsNotNone(request_obj.applied_binding)
        self.assertEqual(FarmPolicyBinding.objects.filter(farm=self.farm, is_active=True).count(), 1)
        self.assertTrue(
            PolicyActivationEvent.objects.filter(
                activation_request=request_obj,
                action=PolicyActivationEvent.ACTION_APPLIED,
            ).exists()
        )

    def test_policy_version_becomes_immutable_after_approval(self):
        package = PolicyPackage.objects.create(
            name="Immutable Package",
            slug="immutable-package",
            created_by=self.actor,
            updated_by=self.actor,
        )
        version = PolicyEngineService.create_version(
            actor=self.actor,
            package=package,
            version_label="v1",
            payload=PolicyEngineService.default_policy_payload(),
        )
        PolicyEngineService.approve_version(actor=self.actor, instance=version)

        with self.assertRaises(ValidationError):
            PolicyEngineService.update_version(
                actor=self.actor,
                instance=version,
                payload=PolicyEngineService.default_policy_payload(),
            )

    def test_activation_eligibility_reports_diff_and_warnings(self):
        package = PolicyEngineService.create_package(
            actor=self.actor,
            name="Eligibility Package",
            slug="eligibility-package",
            description="Eligibility test package.",
        )
        payload = PolicyEngineService.default_policy_payload()
        payload["dual_mode_policy"]["mode"] = FarmSettings.MODE_STRICT
        payload["dual_mode_policy"]["approval_profile"] = FarmSettings.APPROVAL_PROFILE_TIERED
        payload["attachment_policy"]["attachment_scan_mode"] = FarmSettings.ATTACHMENT_SCAN_MODE_HEURISTIC
        version = PolicyEngineService.create_version(
            actor=self.actor,
            package=package,
            version_label="v1",
            payload=payload,
        )
        PolicyEngineService.approve_version(actor=self.actor, instance=version)

        eligibility = PolicyEngineService.activation_eligibility(farm=self.farm, policy_version=version)

        self.assertTrue(eligibility["eligible"])
        self.assertGreater(eligibility["diff"]["changed_count"], 0)
        self.assertIn("mode", eligibility["simulation"]["changed_fields"])
        self.assertTrue(any("STRICT mode" in warning for warning in eligibility["warnings"]))

    def test_runtime_settings_for_farm_applies_active_binding_projection(self):
        package = PolicyEngineService.create_package(
            actor=self.actor,
            name="Runtime Package",
            slug="runtime-package",
            description="Runtime projection package.",
        )
        payload = PolicyEngineService.default_policy_payload()
        payload["dual_mode_policy"]["mode"] = FarmSettings.MODE_STRICT
        payload["dual_mode_policy"]["approval_profile"] = FarmSettings.APPROVAL_PROFILE_TIERED
        version = PolicyEngineService.create_version(
            actor=self.actor,
            package=package,
            version_label="v1",
            payload=payload,
        )
        PolicyEngineService.approve_version(actor=self.actor, instance=version)
        FarmPolicyBinding.objects.create(
            farm=self.farm,
            policy_version=version,
            reason="runtime test",
            created_by=self.actor,
            approved_by=self.actor,
        )

        runtime_settings = PolicyEngineService.runtime_settings_for_farm(farm=self.farm, settings_obj=self.settings)

        self.assertEqual(runtime_settings.mode, FarmSettings.MODE_STRICT)
        self.assertEqual(getattr(runtime_settings, "_effective_policy_source"), "policy_binding")

    def test_effective_policy_falls_back_cleanly_when_policy_engine_schema_unavailable(self):
        with mock.patch.object(PolicyEngineService, "policy_engine_schema_available", return_value=False):
            resolved = PolicyEngineService.effective_policy_for_farm(farm=self.farm, settings_obj=self.settings)

        self.assertEqual(resolved["source"], "farm_settings")
        self.assertIsNone(resolved["binding"])
        self.assertEqual(resolved["flat_policy"]["mode"], FarmSettings.MODE_SIMPLE)

    def test_create_package_requires_policy_engine_schema(self):
        with mock.patch.object(PolicyEngineService, "policy_engine_schema_available", return_value=False):
            with self.assertRaises(ValidationError):
                PolicyEngineService.create_package(
                    actor=self.actor,
                    name="Unavailable Package",
                    slug="unavailable-package",
                    description="Should fail when schema is unavailable.",
                )

    def test_validate_exception_patch_rejects_forbidden_mode_override(self):
        with self.assertRaises(ValidationError):
            PolicyEngineService.validate_exception_patch(
                farm=self.farm,
                requested_patch={"mode": FarmSettings.MODE_STRICT},
                effective_from=timezone.now(),
                effective_to=timezone.now() + timedelta(days=7),
            )

    def test_apply_exception_request_overlays_effective_policy_without_mutating_binding(self):
        package = PolicyEngineService.create_package(
            actor=self.actor,
            name="Exception Base Package",
            slug="exception-base-package",
            description="Base package for exception overlay.",
        )
        payload = PolicyEngineService.default_policy_payload()
        payload["dual_mode_policy"]["mode"] = FarmSettings.MODE_STRICT
        payload["attachment_policy"]["attachment_scan_mode"] = FarmSettings.ATTACHMENT_SCAN_MODE_CLAMAV
        version = PolicyEngineService.create_version(
            actor=self.actor,
            package=package,
            version_label="v1",
            payload=payload,
        )
        PolicyEngineService.approve_version(actor=self.actor, instance=version)
        activation_request = PolicyEngineService.create_activation_request(
            actor=self.actor,
            farm=self.farm,
            policy_version=version,
            rationale="Apply strict baseline before exception.",
        )
        PolicyEngineService.submit_activation_request(actor=self.actor, instance=activation_request)
        PolicyEngineService.approve_activation_request(actor=self.actor, instance=activation_request)
        PolicyEngineService.apply_activation_request(actor=self.actor, instance=activation_request)

        exception_request = PolicyEngineService.create_exception_request(
            actor=self.actor,
            farm=self.farm,
            requested_patch={
                "mandatory_attachment_for_cash": False,
                "attachment_scan_mode": FarmSettings.ATTACHMENT_SCAN_MODE_HEURISTIC,
            },
            rationale="Temporary field exception.",
            effective_from=timezone.now(),
            effective_to=timezone.now() + timedelta(days=3),
        )
        PolicyEngineService.submit_exception_request(actor=self.actor, instance=exception_request)
        PolicyEngineService.approve_exception_request(actor=self.actor, instance=exception_request)
        PolicyEngineService.apply_exception_request(actor=self.actor, instance=exception_request)

        resolved = PolicyEngineService.effective_policy_for_farm(farm=self.farm, settings_obj=self.settings)

        self.assertEqual(resolved["source"], "policy_binding+exception")
        self.assertEqual(
            resolved["flat_policy"]["attachment_scan_mode"],
            FarmSettings.ATTACHMENT_SCAN_MODE_HEURISTIC,
        )
        self.assertFalse(resolved["flat_policy"]["mandatory_attachment_for_cash"])
        self.assertIsNotNone(resolved["exception_request"])
        exception_request.refresh_from_db()
        self.assertEqual(exception_request.status, PolicyExceptionRequest.STATUS_APPLIED)
        self.assertTrue(
            PolicyExceptionEvent.objects.filter(
                exception_request=exception_request,
                action=PolicyExceptionEvent.ACTION_APPLIED,
            ).exists()
        )
        self.assertEqual(FarmPolicyBinding.objects.filter(farm=self.farm, is_active=True).count(), 1)

    def test_diff_policy_version_against_other_version_reports_changed_fields(self):
        package = PolicyEngineService.create_package(
            actor=self.actor,
            name="Diff Package",
            slug="diff-package",
            description="Package for diff testing.",
        )
        payload_v1 = PolicyEngineService.default_policy_payload()
        payload_v2 = PolicyEngineService.default_policy_payload()
        payload_v2["dual_mode_policy"]["mode"] = FarmSettings.MODE_STRICT
        payload_v2["attachment_policy"]["mandatory_attachment_for_cash"] = False
        version_v1 = PolicyEngineService.create_version(
            actor=self.actor,
            package=package,
            version_label="v1",
            payload=payload_v1,
        )
        version_v2 = PolicyEngineService.create_version(
            actor=self.actor,
            package=package,
            version_label="v2",
            payload=payload_v2,
        )

        diff = PolicyEngineService.diff_policy_version(
            policy_version=version_v2,
            compare_to_version=version_v1,
        )

        self.assertEqual(diff["comparison_mode"], "version_to_version")
        self.assertIn("mode", diff["changed_fields"])
        self.assertIn("mandatory_attachment_for_cash", diff["changed_fields"])

    def test_package_usage_snapshot_counts_bindings_and_exception_farms(self):
        package = PolicyEngineService.create_package(
            actor=self.actor,
            name="Usage Package",
            slug="usage-package",
            description="Usage snapshot package.",
        )
        version = PolicyEngineService.create_version(
            actor=self.actor,
            package=package,
            version_label="v1",
            payload=PolicyEngineService.default_policy_payload(),
        )
        PolicyEngineService.approve_version(actor=self.actor, instance=version)
        FarmPolicyBinding.objects.create(
            farm=self.farm,
            policy_version=version,
            reason="usage snapshot",
            created_by=self.actor,
            approved_by=self.actor,
        )
        exception_request = PolicyEngineService.create_exception_request(
            actor=self.actor,
            farm=self.farm,
            requested_patch={"mandatory_attachment_for_cash": False},
            rationale="usage snapshot exception",
            effective_from=timezone.now(),
            effective_to=timezone.now() + timedelta(days=2),
        )
        PolicyEngineService.submit_exception_request(actor=self.actor, instance=exception_request)

        snapshot = PolicyEngineService.package_usage_snapshot()

        self.assertEqual(snapshot["summary"]["packages"], 1)
        self.assertEqual(snapshot["summary"]["active_bindings"], 1)
        self.assertEqual(snapshot["summary"]["farms_with_exceptions"], 1)
        self.assertEqual(snapshot["packages"][0]["exception_farm_count"], 1)

    def test_activation_timeline_snapshot_reports_counts_and_events(self):
        package = PolicyEngineService.create_package(
            actor=self.actor,
            name="Timeline Package",
            slug="timeline-package",
            description="Timeline snapshot package.",
        )
        version = PolicyEngineService.create_version(
            actor=self.actor,
            package=package,
            version_label="v1",
            payload=PolicyEngineService.default_policy_payload(),
        )
        PolicyEngineService.approve_version(actor=self.actor, instance=version)
        request_obj = PolicyEngineService.create_activation_request(
            actor=self.actor,
            farm=self.farm,
            policy_version=version,
            rationale="timeline snapshot",
        )
        PolicyEngineService.submit_activation_request(actor=self.actor, instance=request_obj)

        snapshot = PolicyEngineService.activation_timeline_snapshot()

        self.assertIn("pending", snapshot["counts_by_status"])
        self.assertGreaterEqual(len(snapshot["latest_requests"]), 1)
        self.assertGreaterEqual(len(snapshot["latest_events"]), 1)

    def test_exception_pressure_snapshot_groups_by_farm_and_field_family(self):
        request_obj = PolicyEngineService.create_exception_request(
            actor=self.actor,
            farm=self.farm,
            requested_patch={"attachment_scan_mode": FarmSettings.ATTACHMENT_SCAN_MODE_HEURISTIC},
            rationale="pressure snapshot",
            effective_from=timezone.now(),
            effective_to=timezone.now() + timedelta(days=3),
        )
        PolicyEngineService.submit_exception_request(actor=self.actor, instance=request_obj)

        snapshot = PolicyEngineService.exception_pressure_snapshot()

        self.assertGreaterEqual(len(snapshot["open_by_farm"]), 1)
        self.assertIn("attachment_policy", snapshot["open_by_field_family"])
