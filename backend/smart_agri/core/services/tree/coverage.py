import logging
from typing import Any, Dict, Sequence, Tuple

from django.core.exceptions import ValidationError
from django.db import transaction, connection
from smart_agri.core.models import (
    Activity,
    LocationTreeStock,
    TreeServiceCoverage,
)

logger = logging.getLogger(__name__)


class TreeCoverageService:
    """
    Service responsible for managing TreeServiceCoverage records.
    Extracted from TreeInventoryService (Refactor Phase 3).
    """

    def sync_service_coverages(
        self,
        *,
        activity: Activity,
        entries: Sequence[Dict[str, Any]],
        recorded_by=None,
    ) -> None:
        """
        Ensure TreeServiceCoverage rows for an activity reflect the provided payload.
        The operation is idempotent and safely updates or removes stale rows.
        """
        if activity is None:
            raise ValidationError({"service_counts": "activity is required"})

        payloads = list(entries or [])
        with transaction.atomic():
            existing_qs = TreeServiceCoverage.objects.filter(activity=activity)
            if connection.vendor == "postgresql":
                existing_qs = existing_qs.select_for_update()
            
            existing_map: Dict[Tuple[int, str], TreeServiceCoverage] = {
                (coverage.crop_variety_id, coverage.service_scope): coverage
                for coverage in existing_qs
            }

            if not payloads:
                if existing_map:
                    TreeServiceCoverage.objects.filter(
                        pk__in=[cov.pk for cov in existing_map.values()]
                    ).delete()
                return

            seen_keys: set[Tuple[int, str]] = set()
            log = getattr(activity, "log", None)

            for payload in payloads:
                location = payload.get("location")
                variety = payload.get("crop_variety")
                if not location or not variety:
                    raise ValidationError(
                        {"service_counts": "location and crop variety must be provided."}
                    )

                service_scope = (
                    payload.get("service_scope")
                    or payload.get("service_type")
                    or TreeServiceCoverage.GENERAL
                )
                service_type = payload.get("service_type") or service_scope
                key = (variety.pk, service_scope)
                seen_keys.add(key)

                service_count = int(payload.get("service_count") or 0)
                total_before = payload.get("total_before")
                total_after = payload.get("total_after")
                notes = payload.get("notes") or ""

                if service_count < 0:
                    raise ValidationError(
                        {"service_counts": "service_count cannot be negative."}
                    )

                stock = (
                    LocationTreeStock.objects.filter(
                        location=location,
                        crop_variety=variety,
                    )
                    .only("current_tree_count")
                    .first()
                )
                # Skip validation if activity is part of a plan (future/estimated)
                is_planned = getattr(activity, "crop_plan_id", None) is not None

                if not is_planned and stock and service_count > (stock.current_tree_count or 0):
                    raise ValidationError(
                        {
                            "service_counts": (
                                "service_count ({}) exceeds current tree count ({}) for this site and variety"
                            ).format(service_count, stock.current_tree_count)
                        }
                    )

                # Derived Farm Logic
                farm = None
                if location:
                    farm = location.farm
                elif activity.location:
                    farm = activity.location.farm
                # If still no farm, and the model requires it, we have a problem.
                # Assuming activity.location is reliable or passed location implies farm.
                
                defaults: Dict[str, Any] = {
                    "location": location,
                    "trees_covered": service_count,  # Mapped from service_count
                    "service_type": service_type,
                    "target_scope": service_scope,   # Mapped from service_scope
                    # "total_before": total_before,  # Removed: field does not exist on model
                    # "total_after": total_after,    # Removed: field does not exist on model
                    "notes": notes,
                    # "source_log": log,             # Removed: field does not exist on model (it's related via activity)
                }
                if recorded_by is not None:
                    defaults["recorded_by"] = recorded_by
                
                # Ensure farm is set if creating
                if farm:
                    defaults["farm"] = farm

                existing = existing_map.get(key)
                if existing is None:
                    if not farm:
                         # Fallback or error? Logic implies location is required, so farm should be derivable.
                         # If location is null (SCOPE_FARM?), we need activity.farm or similar.
                         # Model allows location=null.
                         pass

                    new_record = TreeServiceCoverage.objects.create(
                        activity=activity,
                        crop_variety=variety,
                        **defaults
                    )
                    existing_map[key] = new_record
                    continue

                update_fields: list[str] = []
                for attr, value in defaults.items():
                    if getattr(existing, attr) != value:
                        setattr(existing, attr, value)
                        update_fields.append(attr)
                if update_fields:
                    existing.save(update_fields=update_fields)

            stale_ids = [cov.pk for key, cov in existing_map.items() if key not in seen_keys]
            if stale_ids:
                TreeServiceCoverage.objects.filter(pk__in=stale_ids).delete()
