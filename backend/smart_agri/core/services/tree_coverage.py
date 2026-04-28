import logging
from typing import Any, Dict, Sequence, Tuple

from django.core.exceptions import ValidationError
from django.db import transaction, connection
from smart_agri.core.models import (
    Activity,
    BiologicalAssetCohort,
    Location,
    CropVariety,
    LocationTreeStock,
    TreeServiceCoverage,
)

logger = logging.getLogger(__name__)


class TreeCoverageService:
    """
    Service responsible for managing TreeServiceCoverage records.
    Flattened from services.tree.coverage.
    """

    @staticmethod
    def _available_tree_capacity(*, activity: Activity, location: Location, variety: CropVariety) -> int:
        stock = (
            LocationTreeStock.objects.filter(
                location=location,
                crop_variety=variety,
            )
            .only("current_tree_count")
            .first()
        )
        current_stock = int(getattr(stock, "current_tree_count", 0) or 0)
        if current_stock > 0:
            return current_stock

        cohort_quantities = BiologicalAssetCohort.objects.filter(
            deleted_at__isnull=True,
            farm_id=getattr(activity.log, "farm_id", None),
            location=location,
            variety=variety,
            status__in=[
                BiologicalAssetCohort.STATUS_JUVENILE,
                BiologicalAssetCohort.STATUS_PRODUCTIVE,
                BiologicalAssetCohort.STATUS_SICK,
                BiologicalAssetCohort.STATUS_RENEWING,
            ],
        ).values_list("quantity", flat=True)
        return sum(int(quantity or 0) for quantity in cohort_quantities)

    @staticmethod
    def _normalize_distribution_mode(value: Any) -> Any:
        if not isinstance(value, str):
            return value
        aliases = {
            "equal": TreeServiceCoverage.DISTRIBUTION_UNIFORM,
            "equally": TreeServiceCoverage.DISTRIBUTION_UNIFORM,
            "weighted": TreeServiceCoverage.DISTRIBUTION_EXCEPTION_WEIGHTED,
        }
        return aliases.get(value.strip().lower(), value)

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
            
            existing_map: Dict[Tuple[int, int, str], TreeServiceCoverage] = {
                (coverage.location_id or 0, coverage.crop_variety_id, coverage.service_scope): coverage
                for coverage in existing_qs
            }

            if not payloads:
                if existing_map:
                    TreeServiceCoverage.objects.filter(
                        pk__in=[cov.pk for cov in existing_map.values()]
                    ).delete()
                return

            seen_keys: set[Tuple[int, int, str]] = set()
            log = getattr(activity, "log", None)

            for payload in payloads:
                location = payload.get("location")
                variety = payload.get("crop_variety")
                location_id = payload.get("location_id")
                variety_id = payload.get("variety_id") or payload.get("crop_variety_id")
                if location is None and location_id:
                    location = Location.objects.filter(pk=location_id).first()
                if variety is None and variety_id:
                    variety = CropVariety.objects.filter(pk=variety_id).first()
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
                key = (location.pk, variety.pk, service_scope)
                seen_keys.add(key)

                service_count = int(payload.get("service_count") or 0)
                distribution_mode = (
                    payload.get("distribution_mode") or TreeServiceCoverage.DISTRIBUTION_UNIFORM
                )
                distribution_mode = self._normalize_distribution_mode(distribution_mode)
                distribution_factor = payload.get("distribution_factor")
                total_before = payload.get("total_before")
                total_after = payload.get("total_after")
                notes = payload.get("notes") or ""

                if service_count < 0:
                    raise ValidationError(
                        {"service_counts": "service_count cannot be negative."}
                    )

                available_capacity = self._available_tree_capacity(
                    activity=activity,
                    location=location,
                    variety=variety,
                )
                # Skip validation if activity is part of a plan (future/estimated)
                is_planned = getattr(activity, "crop_plan_id", None) is not None
                is_positive_delta = int(getattr(activity, "tree_count_delta", 0) or 0) > 0

                if not is_planned and not is_positive_delta and service_count > available_capacity:
                    raise ValidationError(
                        {
                            "service_counts": (
                                "service_count ({}) exceeds current tree count ({}) for this site and variety"
                            ).format(service_count, available_capacity)
                        }
                    )

                # Derived Farm Logic
                farm = None
                if location:
                    farm = location.farm
                elif activity.location:
                    farm = activity.location.farm
                
                defaults: Dict[str, Any] = {
                    "location": location,
                    "trees_covered": service_count,  # Mapped from service_count
                    "service_type": service_type,
                    "target_scope": service_scope,   # Mapped from service_scope
                    "distribution_mode": distribution_mode,
                    "distribution_factor": distribution_factor or 0,
                    "notes": notes,
                }
                if recorded_by is not None:
                    defaults["recorded_by"] = recorded_by
                
                # Ensure farm is set if creating
                if farm:
                    defaults["farm"] = farm

                existing = existing_map.get(key)
                if existing is None:
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
