from rest_framework import serializers
from smart_agri.finance.models import CostConfiguration
from smart_agri.core.models.settings import FarmSettings
from smart_agri.core.services.policy_engine_service import PolicyEngineService

class CostConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CostConfiguration
        fields = "__all__"

class FarmSettingsSerializer(serializers.ModelSerializer):
    mode_label = serializers.CharField(read_only=True)
    visibility_level = serializers.CharField(read_only=True)
    policy_snapshot = serializers.SerializerMethodField()
    effective_policy_payload = serializers.SerializerMethodField()
    effective_policy_flat = serializers.SerializerMethodField()
    policy_source = serializers.SerializerMethodField()
    active_policy_binding = serializers.SerializerMethodField()
    active_policy_exception = serializers.SerializerMethodField()
    policy_field_catalog = serializers.SerializerMethodField()
    legacy_mode_divergence = serializers.SerializerMethodField()
    policy_validation_errors = serializers.SerializerMethodField()
    effective_policy_fields = serializers.SerializerMethodField()

    def _effective_policy(self, obj):
        cache = getattr(self, "_effective_policy_cache", {})
        cache_key = getattr(obj, "pk", None) or id(obj)
        if cache_key not in cache:
            cache[cache_key] = PolicyEngineService.effective_policy_for_farm(farm=obj.farm, settings_obj=obj)
            self._effective_policy_cache = cache
        return cache[cache_key]

    def get_policy_snapshot(self, obj):
        return obj.policy_snapshot()

    def get_effective_policy_payload(self, obj):
        return self._effective_policy(obj)["policy_payload"]

    def get_effective_policy_flat(self, obj):
        return self._effective_policy(obj)["flat_policy"]

    def get_policy_source(self, obj):
        return self._effective_policy(obj)["source"]

    def get_active_policy_binding(self, obj):
        return self._effective_policy(obj)["binding_summary"]

    def get_active_policy_exception(self, obj):
        return PolicyEngineService._exception_summary(self._effective_policy(obj).get("exception_request"))

    def get_policy_field_catalog(self, obj):
        return obj.policy_field_catalog()

    def get_policy_validation_errors(self, obj):
        return self._effective_policy(obj)["validation_errors"]

    def get_effective_policy_fields(self, obj):
        resolved = self._effective_policy(obj)
        return PolicyEngineService._effective_field_metadata(
            resolved_flat=resolved["flat_policy"],
            field_sources=resolved.get("field_sources") or {},
            field_catalog=obj.policy_field_catalog(),
        )

    def get_legacy_mode_divergence(self, obj):
        global_settings = self.context.get("global_settings")
        if global_settings is None:
            return {"detected": False, "warning": ""}
        return PolicyEngineService.policy_divergence(settings_obj=obj, global_settings=global_settings)

    def validate(self, data):
        # Merge existing instance data with new data to simulate the final state
        # Then run the model's clean() method to enforce DB-level validations
        if self.instance:
            mock_instance = self.Meta.model(**{
                **{f.name: getattr(self.instance, f.name) for f in self.Meta.model._meta.fields},
                **data
            })
        else:
            mock_instance = self.Meta.model(**data)
            
        mock_instance.clean()
        return data

    class Meta:
        model = FarmSettings
        fields = [
            "id",
            "farm",
            "mode",
            "mode_label",
            "visibility_level",
            "enable_zakat",
            "enable_depreciation",
            "show_finance_in_simple",
            "show_stock_in_simple",
            "show_employees_in_simple",
            "show_advanced_reports",
            "enable_sharecropping",
            "sharecropping_mode",
            "enable_petty_cash",
            "variance_behavior",
            "cost_visibility",
            "approval_profile",
            "contract_mode",
            "treasury_visibility",
            "fixed_asset_mode",
            "procurement_committee_threshold",
            "remote_site",
            "single_finance_officer_allowed",
            "local_finance_threshold",
            "sector_review_threshold",
            "mandatory_attachment_for_cash",
            "weekly_remote_review_required",
            "attachment_transient_ttl_days",
            "approved_attachment_archive_after_days",
            "attachment_max_upload_size_mb",
            "attachment_scan_mode",
            "attachment_require_clean_scan_for_strict",
            "attachment_enable_cdr",
            "allow_overlapping_crop_plans",
            "allow_multi_location_activities",
            "allow_cross_plan_activities",
            "allow_creator_self_variance_approval",
            "show_daily_log_smart_card",
            "sales_tax_percentage",
            "enable_multi_currency",
            "default_currency",
            "enable_pos_barcode",
            "enable_tree_gis_zoning",
            "enable_bulk_cohort_transition",
            "enable_biocost_depreciation_predictor",
            "offline_cache_retention_days",
            "synced_draft_retention_days",
            "dead_letter_retention_days",
            "enable_offline_media_purge",
            "enable_offline_conflict_resolution",
            "enable_predictive_alerts",
            "enable_local_purge_audit",
            "policy_snapshot",
            "effective_policy_payload",
            "effective_policy_flat",
            "policy_source",
            "active_policy_binding",
            "active_policy_exception",
            "policy_field_catalog",
            "legacy_mode_divergence",
            "policy_validation_errors",
            "effective_policy_fields",
        ]
        read_only_fields = [
            "farm",
            "mode_label",
            "visibility_level",
            "policy_snapshot",
            "effective_policy_payload",
            "effective_policy_flat",
            "policy_source",
            "active_policy_binding",
            "active_policy_exception",
            "policy_field_catalog",
            "legacy_mode_divergence",
            "policy_validation_errors",
            "effective_policy_fields",
        ]
        extra_kwargs = {
            "show_finance_in_simple": {
                "help_text": "Compatibility-only, display-only, not authoring authority in SIMPLE.",
            },
            "show_stock_in_simple": {
                "help_text": "Compatibility-only, display-only, not authoring authority in SIMPLE.",
            },
            "show_employees_in_simple": {
                "help_text": "Compatibility-only, display-only, not authoring authority in SIMPLE.",
            },
        }
