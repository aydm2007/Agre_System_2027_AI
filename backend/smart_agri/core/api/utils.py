"""
API Utilities
"""
import re
import math
import json
import unicodedata
import csv
import logging
from decimal import Decimal, InvalidOperation
from typing import Any, List, Optional
from django.http import HttpResponse
from django.utils.dateparse import parse_date
from django.core.exceptions import ValidationError
from django.db import OperationalError, connection

TEAM_SPLIT_PATTERN = re.compile(r"[\n\r,;|\u061B\u060C]+")
logger = logging.getLogger(__name__)


def _clean_team_token(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    candidate = unicodedata.normalize('NFKC', value.strip())
    return re.sub(r"\s{2,}", " ", candidate)


def _tokenize_team_field(raw_value: Any) -> List[str]:
    if isinstance(raw_value, (list, tuple)):
        tokens: List[str] = []
        for entry in raw_value:
            cleaned = _clean_team_token(entry)
            if cleaned:
                tokens.append(cleaned)
        return tokens

    if not isinstance(raw_value, str):
        return []

    normalised = unicodedata.normalize('NFKC', raw_value)
    normalised = normalised.replace('\r\n', '\n')
    parts = TEAM_SPLIT_PATTERN.split(normalised)

    tokens: List[str] = []
    for part in parts:
        cleaned = _clean_team_token(part)
        if cleaned:
            tokens.append(cleaned)

    if not tokens:
        fallback = _clean_team_token(raw_value)
        if fallback:
            tokens.append(fallback)

    return tokens


def _csv_response(filename: str, headers, rows):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    return response


def _parse_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if value in (None, ""):
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    return text in {"1", "true", "t", "yes", "y", "on"}


def _coerce_int(value):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _safe_decimal(value, default="0"):
    if value in (None, ""):
        return Decimal(default)

    candidate = value
    if isinstance(candidate, Decimal):
        return candidate if candidate.is_finite() else Decimal(default)

    try:
        result = Decimal(str(candidate))
    except (TypeError, ValueError, InvalidOperation):
        logger.warning("Invalid decimal input received; using default.", extra={"value": value})
        return Decimal(default)

    if not result.is_finite():
        logger.warning("Non-finite decimal input received; using default.", extra={"value": value})
        return Decimal(default)
    return result


def _strict_decimal(value):
    if value in (None, ""):
        return None
    if isinstance(value, Decimal):
        return value if value.is_finite() else None
    try:
        result = Decimal(str(value))
    except (TypeError, ValueError, InvalidOperation):
        return None
    return result if result.is_finite() else None


def _safe_float(value, default=0.0):
    raise RuntimeError("FORBIDDEN_IN_GUARDED_CONTEXT: Use _safe_decimal instead.")


def _coerce_int_list(value):
    if value in (None, ""):
        return []
    if isinstance(value, (list, tuple, set)):
        tokens = value
    else:
        tokens = str(value).split(',')
    cleaned = []
    for token in tokens:
        try:
            cleaned.append(int(str(token).strip()))
        except (TypeError, ValueError):
            continue
    return cleaned


def _coerce_bool(value):
    if isinstance(value, bool):
        return value
    if value in (None, ""):
        return False
    if isinstance(value, (int, float)):
        return value != 0
    candidate = str(value).strip().lower()
    if not candidate:
        return False
    return candidate in {"1", "true", "t", "yes", "y", "on", "all"}


def _gather_tree_filters(params):
    filters = {}
    raw_filters = params.get('tree_filters')
    if raw_filters:
        try:
            parsed = json.loads(raw_filters)
        except (TypeError, ValueError):
            parsed = {}
        if isinstance(parsed, dict):
            filters.update({k: v for k, v in parsed.items() if v not in (None, "")})
    for key in (
        'farm',
        'farm_id',
        'location',
        'location_id',
        'variety_id',
        'status_code',
        'planted_after',
        'planted_before',
    ):
        qp_key = f'tree_{key}'
        value = params.get(qp_key)
        if value not in (None, ""):
            filters[key] = value
    return filters


def _apply_tree_filters(queryset, filters):
    sanitized = {}
    farm_value = filters.get('farm_id') or filters.get('farm')
    farm_ids = _coerce_int_list(farm_value)
    if farm_ids:
        queryset = queryset.filter(location__farm_id__in=farm_ids)
        sanitized['farm_ids'] = farm_ids

    location_value = filters.get('location_id') or filters.get('location')
    location_id = _coerce_int(location_value)
    if location_id is not None:
        queryset = queryset.filter(location_id=location_id)
        sanitized['location_id'] = location_id

    variety_value = filters.get('variety_id')
    variety_id = _coerce_int(variety_value)
    if variety_id is not None:
        queryset = queryset.filter(crop_variety_id=variety_id)
        sanitized['variety_id'] = variety_id

    status_code = filters.get('status_code')
    if status_code:
        queryset = queryset.filter(productivity_status__code=status_code)
        sanitized['status_code'] = status_code

    planted_after = filters.get('planted_after')
    if planted_after:
        parsed_after = parse_date(planted_after) if isinstance(planted_after, str) else planted_after
        if parsed_after:
            queryset = queryset.filter(planting_date__gte=parsed_after)
            sanitized['planted_after'] = parsed_after.isoformat()

    planted_before = filters.get('planted_before')
    if planted_before:
        parsed_before = parse_date(planted_before) if isinstance(planted_before, str) else planted_before
        if parsed_before:
            queryset = queryset.filter(planting_date__lte=parsed_before)
            sanitized['planted_before'] = parsed_before.isoformat()

    return queryset, sanitized


def _sync_pk_sequence(model):
    """Ensure the PostgreSQL sequence for model's id is ahead of MAX(id)."""
    table = model._meta.db_table
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT pg_get_serial_sequence(%s, %s)", [table, 'id'])
            row = cur.fetchone()
            if not row or not row[0]:
                return
            seq_name = row[0]
            cur.execute(f"SELECT COALESCE(MAX(id), 0) FROM {table}")
            max_id = cur.fetchone()[0] or 0
            next_val = int(max_id) + 1
            cur.execute("SELECT setval(%s, %s, false)", [seq_name, next_val])
    except (ValidationError, OperationalError, ValueError) as e:
        logger.warning("_sync_pk_sequence failed: %s", e)
