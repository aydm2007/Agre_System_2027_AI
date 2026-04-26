from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.exceptions import PermissionDenied

from smart_agri.core.api.permissions import user_farm_ids
from smart_agri.core.api.utils import _coerce_int, _gather_tree_filters, _parse_bool
from smart_agri.core.models import Activity, DailyLog, Farm


@dataclass(frozen=True)
class AdvancedReportContext:
    start: object
    end: object
    farm_ids: list[int]
    season_id: int | None
    crop_id: int | None
    task_id: int | None
    location_id: int | None
    include_tree_inventory: bool
    tree_filters: dict
    include_details: bool
    section_scope: list[str]
    section_scope_explicit: bool


MAX_ADVANCED_REPORT_SPAN_DAYS = 180
DEFAULT_ADVANCED_REPORT_SECTIONS = ["summary"]
ADVANCED_REPORT_TREE_SECTIONS = {"tree_summary", "tree_events"}
ADVANCED_REPORT_DETAIL_SECTIONS = {"activities", "charts", "detailed_tables"}


def _normalize_section_scope(raw_value) -> list[str]:
    if raw_value in (None, "", []):
        return list(DEFAULT_ADVANCED_REPORT_SECTIONS)

    values: list[str] = []
    if isinstance(raw_value, (list, tuple, set)):
        values = [str(value).strip() for value in raw_value if str(value).strip()]
    else:
        candidate = str(raw_value).strip()
        if candidate.startswith("[") and candidate.endswith("]"):
            try:
                import json

                parsed = json.loads(candidate)
                if isinstance(parsed, list):
                    values = [str(value).strip() for value in parsed if str(value).strip()]
            except (TypeError, ValueError):
                values = []
        if not values:
            values = [part.strip() for part in candidate.split(",") if part.strip()]

    normalized: list[str] = []
    for value in values:
        if value not in normalized:
            normalized.append(value)
    return normalized or list(DEFAULT_ADVANCED_REPORT_SECTIONS)


def _normalize_date_range(*, start_param: str | None, end_param: str | None):
    today = timezone.now().date()
    start = parse_date(start_param) if start_param else (today - timedelta(days=30))
    end = parse_date(end_param) if end_param else today
    if start is None:
        start = today - timedelta(days=30)
    if end is None:
        end = today
    if start > end:
        start, end = end, start
    span_days = (end - start).days
    if span_days > MAX_ADVANCED_REPORT_SPAN_DAYS:
        start = end - timedelta(days=MAX_ADVANCED_REPORT_SPAN_DAYS)
    return start, end


def _resolve_permitted_farm_ids(*, user, farm_param: str | None) -> list[int]:
    accessible_ids = set(user_farm_ids(user))
    requested_ids = []
    if farm_param:
        for token in farm_param.split(','):
            token = token.strip()
            if token.isdigit():
                requested_ids.append(int(token))

    if getattr(user, 'is_superuser', False):
        if requested_ids:
            return requested_ids
        if accessible_ids:
            return list(accessible_ids)
        return list(Farm.objects.values_list('id', flat=True))

    farm_ids = [fid for fid in requested_ids if fid in accessible_ids] if requested_ids else list(accessible_ids)
    if not farm_ids:
        raise PermissionDenied("ليس لديك صلاحية لعرض هذه البيانات لهذه المزرعة.")
    return farm_ids


def parse_advanced_report_context(request) -> AdvancedReportContext:
    query_params = request.query_params
    section_scope_explicit = "section_scope" in query_params
    raw_section_scope = []
    if hasattr(query_params, "getlist"):
        raw_section_scope = query_params.getlist("section_scope")
    if not raw_section_scope:
        raw_section_scope = query_params.get("section_scope")
    section_scope = _normalize_section_scope(raw_section_scope)
    start, end = _normalize_date_range(
        start_param=query_params.get('start') or query_params.get('start_date'),
        end_param=query_params.get('end') or query_params.get('end_date'),
    )
    include_tree_inventory = bool(
        ADVANCED_REPORT_TREE_SECTIONS.intersection(section_scope)
    ) or _parse_bool(query_params.get('include_tree_inventory'))
    include_details = True
    if section_scope_explicit:
        include_details = bool(
            ADVANCED_REPORT_DETAIL_SECTIONS.intersection(section_scope)
        )
    return AdvancedReportContext(
        start=start,
        end=end,
        farm_ids=_resolve_permitted_farm_ids(
            user=request.user,
            farm_param=query_params.get('farm') or query_params.get('farm_id'),
        ),
        season_id=_coerce_int(query_params.get('season_id') or query_params.get('season')),
        crop_id=_coerce_int(query_params.get('crop_id')),
        task_id=_coerce_int(query_params.get('task_id')),
        location_id=_coerce_int(query_params.get('location') or query_params.get('location_id')),
        include_tree_inventory=include_tree_inventory,
        tree_filters=_gather_tree_filters(query_params) if include_tree_inventory else {},
        include_details=include_details,
        section_scope=section_scope,
        section_scope_explicit=section_scope_explicit,
    )


def build_activity_queryset(*, context: AdvancedReportContext):
    activity_qs = Activity.objects.filter(
        deleted_at__isnull=True,
        log__deleted_at__isnull=True,
        log__log_date__range=(context.start, context.end),
    ).select_related(
        'log', 'log__farm', 'log__supervisor', 'crop', 'task', 'asset', 'well_asset'
    ).prefetch_related('activity_locations__location')

    if context.farm_ids:
        activity_qs = activity_qs.filter(log__farm_id__in=context.farm_ids)
    if context.crop_id is not None:
        activity_qs = activity_qs.filter(crop_id=context.crop_id)
    if context.task_id is not None:
        activity_qs = activity_qs.filter(task_id=context.task_id)
    if context.location_id is not None:
        activity_qs = activity_qs.filter(activity_locations__location_id=context.location_id)
    if context.season_id is not None:
        activity_qs = activity_qs.filter(crop_plan__season_id=context.season_id)
    return activity_qs


def build_recent_logs_payload(*, activity_qs):
    recent_logs_qs = (
        DailyLog.objects.filter(
            deleted_at__isnull=True,
            id__in=activity_qs.values_list('log_id', flat=True),
        )
        .select_related('farm', 'supervisor')
        .annotate(activity_count=Count('activities', filter=Q(activities__deleted_at__isnull=True)))
        .order_by('-log_date', '-id')[:5]
    )
    payload = []
    for log in recent_logs_qs:
        payload.append({
            'id': log.id,
            'date': log.log_date.isoformat() if log.log_date else None,
            'notes': log.notes,
            'activity_count': log.activity_count or 0,
            'farm': {'id': log.farm_id, 'name': log.farm.name} if log.farm else None,
            'supervisor': log.supervisor.name if log.supervisor else None,
        })
    return payload
