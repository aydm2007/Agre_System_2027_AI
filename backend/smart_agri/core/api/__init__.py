"""Public API surface with lazy exports to avoid importing router/viewsets eagerly."""

from importlib import import_module

from .permissions import (
    MANAGER_ROLES,
    IsFarmManager,
    FarmScopedPermission,
    user_farm_ids,
    _user_is_farm_manager,
    _ensure_user_has_farm_access,
    _limit_queryset_to_user_farms,
)
from .utils import (
    TEAM_SPLIT_PATTERN,
    _clean_team_token,
    _tokenize_team_field,
    _csv_response,
    _parse_bool,
    _coerce_int,
    _safe_float,
    _coerce_int_list,
    _coerce_bool,
    _gather_tree_filters,
    _sync_pk_sequence,
)
from smart_agri.core.services.tree_inventory import TreeInventoryService

_LAZY_EXPORTS = {
    "router": (".router", "router"),
    "advanced_report": (".reporting", "advanced_report"),
    "dashboard_stats": (".reporting", "dashboard_stats"),
    "request_advanced_report_job": (".reporting", "request_advanced_report_job"),
    "advanced_report_job_status": (".reporting", "advanced_report_job_status"),
    "export_templates": (".import_export", "export_templates"),
    "export_jobs": (".import_export", "export_jobs"),
    "create_export_job": (".import_export", "create_export_job"),
    "export_job_status": (".import_export", "export_job_status"),
    "export_job_download": (".import_export", "export_job_download"),
    "import_templates": (".import_export", "import_templates"),
    "import_jobs": (".import_export", "import_jobs"),
    "import_template_download": (".import_export", "import_template_download"),
    "upload_import_job": (".import_export", "upload_import_job"),
    "validate_import_job": (".import_export", "validate_import_job"),
    "import_job_preview": (".import_export", "import_job_preview"),
    "apply_import_job": (".import_export", "apply_import_job"),
    "import_job_error_download": (".import_export", "import_job_error_download"),
}


def __getattr__(name):
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = target
    module = import_module(module_name, __name__)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
