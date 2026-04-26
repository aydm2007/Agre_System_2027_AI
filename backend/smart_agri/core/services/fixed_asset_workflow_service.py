from decimal import Decimal

from rest_framework.exceptions import PermissionDenied

from smart_agri.core.services.decimal_guard import coerce_decimal, safe_percentage

from smart_agri.core.api.permissions import user_farm_ids
from smart_agri.core.models import Asset, AuditLog
from smart_agri.core.models.settings import FarmSettings
from smart_agri.core.services.mode_policy_service import policy_snapshot_for_farm


class FixedAssetWorkflowService:
    """Read-model service for governed fixed-asset dashboards and workflow posture."""

    @staticmethod
    def _line_amounts_visible(policy_snapshot) -> bool:
        return (
            policy_snapshot["visibility_level"] == "full_erp"
            and policy_snapshot["cost_visibility"] == FarmSettings.COST_VISIBILITY_FULL
        )

    @classmethod
    def _serialize_asset(cls, *, asset: Asset, policy_snapshot):
        purchase_value = coerce_decimal(asset.purchase_value, places=Decimal("0.01"))
        accumulated = coerce_decimal(asset.accumulated_depreciation, places=Decimal("0.01"))
        salvage = coerce_decimal(asset.salvage_value, places=Decimal("0.01"))
        depreciable_base = (purchase_value - salvage).quantize(Decimal("0.01"))
        depreciation_percentage = Decimal("0.00")
        if depreciable_base > 0:
            depreciation_percentage = safe_percentage(accumulated, depreciable_base, places=Decimal("0.01"))

        line_amounts_visible = cls._line_amounts_visible(policy_snapshot)
        payload = {
            "id": asset.id,
            "name": asset.name,
            "code": asset.code,
            "category": asset.category,
            "asset_type": asset.asset_type,
            "status": asset.status,
            "farm_id": asset.farm_id,
            "farm_name": asset.farm.name,
            "purchase_date": asset.purchase_date.isoformat() if asset.purchase_date else None,
            "purchase_value": str(purchase_value.quantize(Decimal("0.01"))) if line_amounts_visible else None,
            "salvage_value": str(salvage.quantize(Decimal("0.01"))) if line_amounts_visible else None,
            "accumulated_depreciation": str(accumulated.quantize(Decimal("0.01"))) if line_amounts_visible else None,
            "book_value": str((purchase_value - accumulated).quantize(Decimal("0.01"))) if line_amounts_visible else None,
            "operational_cost_per_hour": (
                str(coerce_decimal(asset.operational_cost_per_hour, places=Decimal("0.01")))
                if line_amounts_visible
                else None
            ),
            "useful_life_years": asset.useful_life_years,
            "depreciation_method": asset.depreciation_method,
            "depreciation_percentage": str(depreciation_percentage),
            "health_status": cls._health_status(depreciation_percentage),
            "capitalization_state": cls._capitalization_state(policy_snapshot, asset),
            "policy_snapshot": policy_snapshot,
            "visibility_level": policy_snapshot["visibility_level"],
            "cost_display_mode": policy_snapshot["cost_visibility"],
            "fixed_asset_mode": policy_snapshot["fixed_asset_mode"],
            "amounts_redacted": not line_amounts_visible,
        }
        return payload, purchase_value, accumulated

    @staticmethod
    def _resolve_target_farms(*, user, farm_id):
        accessible_farms = list(user_farm_ids(user))
        if farm_id:
            if not str(farm_id).isdigit():
                raise PermissionDenied("معرف المزرعة غير صالح.")
            farm_id = int(farm_id)
            if not user.is_superuser and farm_id not in accessible_farms:
                raise PermissionDenied("لا تملك صلاحية الوصول إلى هذه المزرعة.")
            return [farm_id]
        return accessible_farms

    @staticmethod
    def _health_status(depreciation_percentage: Decimal) -> str:
        if depreciation_percentage >= Decimal("90"):
            return "CRITICAL"
        if depreciation_percentage >= Decimal("70"):
            return "WARNING"
        return "GREEN"

    @staticmethod
    def _capitalization_state(policy_snapshot, asset: Asset) -> str:
        if policy_snapshot["fixed_asset_mode"] == FarmSettings.FIXED_ASSET_MODE_FULL_CAPITALIZATION:
            if asset.accumulated_depreciation and Decimal(str(asset.accumulated_depreciation or 0)) > Decimal("0"):
                return "capitalized_and_depreciating"
            return "capitalized"
        return "tracking_only"

    @classmethod
    def build_dashboard_payload(cls, *, user, farm_id=None, category=None):
        target_farms = cls._resolve_target_farms(user=user, farm_id=farm_id)
        if not target_farms and not user.is_superuser:
            return {"count": 0, "results": [], "summary": {}}

        qs = Asset.objects.filter(deleted_at__isnull=True).select_related("farm")
        if target_farms:
            qs = qs.filter(farm_id__in=target_farms)

        if category:
            qs = qs.filter(category__iexact=category)

        policy_snapshot, _settings_obj, _source, _resolved_farm_id = policy_snapshot_for_farm(
            farm_id=target_farms[0] if target_farms else None
        )

        results = []
        total_purchase = Decimal("0.00")
        total_accumulated = Decimal("0.00")
        warning_count = 0
        critical_count = 0
        line_amounts_visible = cls._line_amounts_visible(policy_snapshot)

        for asset in qs.order_by("farm__name", "category", "name"):
            row, purchase_value, accumulated = cls._serialize_asset(
                asset=asset,
                policy_snapshot=policy_snapshot,
            )
            health_status = row["health_status"]
            if health_status == "WARNING":
                warning_count += 1
            elif health_status == "CRITICAL":
                critical_count += 1

            total_purchase += purchase_value
            total_accumulated += accumulated
            results.append(row)

        summary = {
            "assets_count": len(results),
            "categories": sorted({entry["category"] for entry in results}),
            "warning_assets": warning_count,
            "critical_assets": critical_count,
            "total_purchase_value": (
                str(total_purchase.quantize(Decimal("0.01")))
                if policy_snapshot["cost_visibility"] != FarmSettings.COST_VISIBILITY_RATIOS_ONLY
                else None
            ),
            "total_accumulated_depreciation": (
                str(total_accumulated.quantize(Decimal("0.01")))
                if line_amounts_visible
                else None
            ),
            "report_flags": {
                "requires_capitalization_controls": policy_snapshot["fixed_asset_mode"]
                == FarmSettings.FIXED_ASSET_MODE_FULL_CAPITALIZATION,
                "tracking_only": policy_snapshot["fixed_asset_mode"]
                == FarmSettings.FIXED_ASSET_MODE_TRACKING_ONLY,
                "line_amounts_visible": line_amounts_visible,
            },
        }

        return {
            "count": len(results),
            "results": results,
            "summary": summary,
            "policy_snapshot": policy_snapshot,
            "visibility_level": policy_snapshot["visibility_level"],
            "cost_display_mode": policy_snapshot["cost_visibility"],
        }

    @staticmethod
    def runtime_summary():
        active_assets = Asset.objects.filter(deleted_at__isnull=True)
        return {
            "assets_count": active_assets.count(),
            "full_capitalization_assets": active_assets.filter(
                farm__settings__fixed_asset_mode=FarmSettings.FIXED_ASSET_MODE_FULL_CAPITALIZATION
            ).count(),
            "tracking_only_assets": active_assets.filter(
                farm__settings__fixed_asset_mode=FarmSettings.FIXED_ASSET_MODE_TRACKING_ONLY
            ).count(),
            "depreciating_assets": active_assets.filter(accumulated_depreciation__gt=0).count(),
            "capitalization_posts": AuditLog.objects.filter(action="FIXED_ASSET_CAPITALIZE").count(),
            "disposal_posts": AuditLog.objects.filter(action="FIXED_ASSET_DISPOSE").count(),
        }
