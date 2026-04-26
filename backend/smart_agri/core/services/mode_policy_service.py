"""Canonical mode-policy resolver used by dashboards and API surfaces."""

from django.core.exceptions import ValidationError
from django.db import OperationalError, ProgrammingError

from smart_agri.core.models.farm import Farm
from smart_agri.core.models.settings import FarmSettings, SystemSettings
from smart_agri.core.services.policy_engine_service import PolicyEngineService


TRANSITIONAL_SIMPLE_DISPLAY_FLAGS_NOTE = (
    "compatibility-only, display-only, not authoring authority"
)


def transitional_simple_display_flags_snapshot(settings):
    return {
        "show_finance_in_simple": bool(getattr(settings, "show_finance_in_simple", False)),
        "show_stock_in_simple": bool(getattr(settings, "show_stock_in_simple", False)),
        "show_employees_in_simple": bool(getattr(settings, "show_employees_in_simple", False)),
    }


def build_fallback_settings():
    return FarmSettings(
        mode=FarmSettings.MODE_SIMPLE,
        variance_behavior=FarmSettings.VARIANCE_BEHAVIOR_WARN,
        cost_visibility=FarmSettings.COST_VISIBILITY_SUMMARIZED,
        approval_profile=FarmSettings.APPROVAL_PROFILE_TIERED,
        contract_mode=FarmSettings.CONTRACT_MODE_OPERATIONAL_ONLY,
        treasury_visibility=FarmSettings.TREASURY_VISIBILITY_HIDDEN,
        fixed_asset_mode=FarmSettings.FIXED_ASSET_MODE_TRACKING_ONLY,
        enable_zakat=True,
        enable_depreciation=True,
        enable_sharecropping=False,
        sharecropping_mode=FarmSettings.SHARECROPPING_MODE_FINANCIAL,
        enable_petty_cash=True,
        allow_overlapping_crop_plans=False,
        allow_multi_location_activities=True,
        allow_cross_plan_activities=False,
        allow_creator_self_variance_approval=False,
        show_daily_log_smart_card=True,
    )


def build_mode_payload(*, settings, global_settings, source, farm_id=None, extra=None):
    strict = settings.mode == FarmSettings.MODE_STRICT
    divergence = PolicyEngineService.policy_divergence(settings_obj=settings, global_settings=global_settings)
    effective_policy = None
    active_binding = None
    if getattr(settings, "farm_id", None):
        resolved = PolicyEngineService.effective_policy_for_farm(farm=settings.farm, settings_obj=settings)
        effective_policy = resolved["policy_payload"]
        active_binding = resolved["binding_summary"]
        active_exception = PolicyEngineService._exception_summary(resolved.get("exception_request"))
        effective_flat = resolved["flat_policy"]
        validation_errors = resolved["validation_errors"]
        policy_source = resolved["source"]
        effective_fields = PolicyEngineService._effective_field_metadata(
            resolved_flat=resolved["flat_policy"],
            field_sources=resolved.get("field_sources") or {},
            field_catalog=FarmSettings.policy_field_catalog(),
        )
    else:
        active_exception = None
        effective_flat = None
        validation_errors = []
        policy_source = source
        effective_fields = []
    payload = {
        "mode": settings.mode,
        "strict_erp_mode": strict,
        "mode_label": settings.mode_label,
        "visibility_level": settings.visibility_level,
        "source": source,
        "farm_id": farm_id,
        "allowed_variance_percentage": str(global_settings.allowed_variance_percentage),
        "cost_display_mode": settings.cost_visibility,
        "policy_snapshot": settings.policy_snapshot(),
        "effective_policy_payload": effective_policy or PolicyEngineService.policy_payload_from_settings(settings=settings),
        "effective_policy_flat": effective_flat or settings.policy_snapshot(),
        "policy_source": policy_source,
        "active_policy_binding": active_binding,
        "active_policy_exception": active_exception,
        "policy_field_catalog": FarmSettings.policy_field_catalog(),
        "policy_validation_errors": validation_errors,
        "effective_policy_fields": effective_fields,
        "legacy_mode_divergence": divergence,
        "legacy_global_strict_erp_mode": bool(global_settings.strict_erp_mode),
    }
    if extra:
        payload.update(extra)
    return payload


def resolve_farm_settings(*, farm=None, farm_id=None):
    source = "farm_settings"
    if farm is None and farm_id is not None:
        farm = Farm.objects.filter(pk=farm_id, deleted_at__isnull=True).first()
        if farm is None:
            return build_fallback_settings(), "fallback:farm_not_found", farm_id

    if farm is None:
        return build_fallback_settings(), "fallback:no_context", None

    try:
        settings, _ = FarmSettings.objects.get_or_create(farm=farm)
    except (ProgrammingError, OperationalError, ValidationError):
        return build_fallback_settings(), "fallback:farm_settings_table_missing", farm.id

    return settings, source, farm.id


def policy_snapshot_for_farm(*, farm=None, farm_id=None):
    settings, source, resolved_farm_id = resolve_farm_settings(farm=farm, farm_id=farm_id)
    return settings.policy_snapshot(), settings, source, resolved_farm_id


def simple_policy_fallback_payload(farm_id):
    settings = build_fallback_settings()
    policy_snapshot = settings.policy_snapshot()
    return {
        "farm": farm_id,
        "mode": settings.mode,
        "mode_label": settings.mode_label,
        "visibility_level": settings.visibility_level,
        "strict_erp_mode": False,
        "source": "fallback:farm_settings_table_missing",
        **policy_snapshot,
        "policy_snapshot": policy_snapshot,
        "effective_policy_payload": PolicyEngineService.policy_payload_from_settings(settings=settings),
        "effective_policy_flat": policy_snapshot,
        "policy_source": "fallback:farm_settings_table_missing",
        "active_policy_binding": None,
        "active_policy_exception": None,
        "policy_field_catalog": FarmSettings.policy_field_catalog(),
        "policy_validation_errors": [],
        "effective_policy_fields": [],
        "legacy_mode_divergence": {"detected": False, "warning": ""},
        "legacy_global_strict_erp_mode": False,
    }


def global_system_settings():
    return SystemSettings.get_settings()


def is_finance_authoring_allowed(*, farm=None, farm_id=None):
    """
    Returns True if the farm is in a mode that permits full financial ledger authoring 
    (i.e. STRICT mode). Returns False for SIMPLE mode.
    """
    settings, _, _ = resolve_farm_settings(farm=farm, farm_id=farm_id)
    return settings.mode == FarmSettings.MODE_STRICT


def allowed_finance_routes(*, farm=None, farm_id=None):
    """
    Returns a list of explicitly safe finance routes based on the farm's active mode.
    Used for frontend navigation restrictions and backend API validation.
    """
    base_routes = [
        "/api/v1/finance/petty-cash/status",
        "/api/v1/finance/supplier-settlement/status",
        "/api/v1/finance/dashboard/summary",
    ]
    if is_finance_authoring_allowed(farm=farm, farm_id=farm_id):
        base_routes.extend([
            "/api/v1/finance/treasury-transactions/",
            "/api/v1/finance/ledger/",
            "/api/v1/finance/petty-cash/disburse/",
            "/api/v1/finance/supplier-settlement/pay/",
        ])
    return base_routes
