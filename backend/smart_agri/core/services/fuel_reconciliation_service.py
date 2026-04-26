from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from django.db.models import Count
from rest_framework.exceptions import PermissionDenied

from smart_agri.core.api.permissions import user_farm_ids
from smart_agri.core.models.log import AuditLog, DailyLog, FuelConsumptionAlert
from smart_agri.core.services.mode_policy_service import policy_snapshot_for_farm
from smart_agri.inventory.models import FuelLog, TankCalibration


class FuelReconciliationService:
    """Read-model service for governed fuel reconciliation dashboards."""

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
    def _normalize_date(value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        return value

    @staticmethod
    def _severity_rank(status):
        return {
            FuelConsumptionAlert.STATUS_OK: 0,
            FuelConsumptionAlert.STATUS_WARNING: 1,
            FuelConsumptionAlert.STATUS_CRITICAL: 2,
        }.get(status or FuelConsumptionAlert.STATUS_OK, 0)

    @classmethod
    def _variance_severity(cls, flags, alert_status):
        if flags["critical_variance"]:
            return "critical"
        if flags["warning_variance"] or alert_status == DailyLog.FUEL_ALERT_STATUS_WARNING:
            return "warning"
        if flags["missing_calibration"] or flags["missing_benchmark"] or flags["no_machine_link"]:
            return "warning"
        return "normal"

    @classmethod
    def _reconciliation_state(cls, flags, alert_status):
        if flags["critical_variance"]:
            return "manager_review_required"
        if flags["warning_variance"] or alert_status == DailyLog.FUEL_ALERT_STATUS_WARNING:
            return "pending_review"
        if flags["missing_calibration"] or flags["missing_benchmark"] or flags["no_machine_link"]:
            return "incomplete_context"
        return "balanced"

    @classmethod
    def build_dashboard_payload(cls, *, user, farm_id=None, tank=None):
        target_farms = cls._resolve_target_farms(user=user, farm_id=farm_id)

        if not target_farms and not user.is_superuser:
            return {"count": 0, "results": [], "summary": {}}

        logs_qs = (
            FuelLog.objects.select_related("farm", "asset_tank", "supervisor")
            .filter(farm_id__in=target_farms)
            .order_by("-reading_date", "asset_tank__name")
        )
        if tank:
            logs_qs = logs_qs.filter(asset_tank_id=tank)

        policy_snapshot, _settings_obj, _source, _resolved_farm_id = policy_snapshot_for_farm(
            farm_id=target_farms[0] if target_farms else None
        )

        dates_by_farm = defaultdict(set)
        for entry in logs_qs:
            reading_day = cls._normalize_date(entry.reading_date)
            if reading_day is not None:
                dates_by_farm[entry.farm_id].add(reading_day)

        daily_logs = DailyLog.objects.none()
        if dates_by_farm:
            daily_logs = DailyLog.objects.filter(
                farm_id__in=dates_by_farm.keys(),
                log_date__in={date for values in dates_by_farm.values() for date in values},
            )

        logs_by_key = {(log.farm_id, log.log_date): log for log in daily_logs}

        alerts_qs = (
            FuelConsumptionAlert.objects.select_related("asset", "log")
            .filter(log_id__in=daily_logs.values_list("id", flat=True))
            .order_by("log__log_date", "asset__name")
        )
        alerts_by_key = defaultdict(list)
        for alert in alerts_qs:
            alerts_by_key[(alert.log.farm_id, alert.log.log_date)].append(alert)

        calibration_counts = dict(
            TankCalibration.objects.filter(asset_id__in=logs_qs.values_list("asset_tank_id", flat=True))
            .values("asset_id")
            .annotate(total=Count("id"))
            .values_list("asset_id", "total")
        )

        results = []
        summary = {
            "logs_count": 0,
            "open_anomalies": 0,
            "warning_logs": 0,
            "critical_logs": 0,
            "missing_calibration_logs": 0,
            "pending_reconciliation_logs": 0,
        }

        for fuel_log in logs_qs:
            reading_day = cls._normalize_date(fuel_log.reading_date)
            matched_daily_log = logs_by_key.get((fuel_log.farm_id, reading_day))
            alerts = alerts_by_key.get((fuel_log.farm_id, reading_day), [])
            expected_liters = sum((Decimal(alert.expected_liters or 0) for alert in alerts), Decimal("0.0000"))
            actual_liters = Decimal(fuel_log.liters_consumed or 0).quantize(Decimal("0.0001"))
            variance_liters = (actual_liters - expected_liters).quantize(Decimal("0.0001"))
            alert_status = getattr(matched_daily_log, "fuel_alert_status", DailyLog.FUEL_ALERT_STATUS_OK)
            highest_alert = alert_status
            for alert in alerts:
                if cls._severity_rank(alert.status) > cls._severity_rank(highest_alert):
                    highest_alert = alert.status

            flags = {
                "missing_calibration": calibration_counts.get(fuel_log.asset_tank_id, 0) == 0,
                "missing_benchmark": any(
                    (Decimal(alert.expected_liters or 0) == Decimal("0.0000"))
                    and "missing fuel consumption benchmark" in str(alert.note or "").lower()
                    for alert in alerts
                ),
                "warning_variance": highest_alert == FuelConsumptionAlert.STATUS_WARNING,
                "critical_variance": highest_alert == FuelConsumptionAlert.STATUS_CRITICAL,
                "no_machine_link": not bool(alerts),
            }

            variance_severity = cls._variance_severity(flags, alert_status)
            reconciliation_state = cls._reconciliation_state(flags, alert_status)
            fuel_alert_status = highest_alert if alerts else alert_status

            if variance_severity != "normal":
                summary["open_anomalies"] += 1
            if flags["warning_variance"]:
                summary["warning_logs"] += 1
            if flags["critical_variance"]:
                summary["critical_logs"] += 1
            if flags["missing_calibration"]:
                summary["missing_calibration_logs"] += 1
            if reconciliation_state != "balanced":
                summary["pending_reconciliation_logs"] += 1

            results.append(
                {
                    "id": fuel_log.id,
                    "farm_id": fuel_log.farm_id,
                    "farm_name": fuel_log.farm.name,
                    "tank_id": fuel_log.asset_tank_id,
                    "tank": fuel_log.asset_tank.name,
                    "tank_code": fuel_log.asset_tank.code,
                    "supervisor": fuel_log.supervisor.name,
                    "reading_date": fuel_log.reading_date.isoformat() if fuel_log.reading_date else None,
                    "measurement_method": fuel_log.measurement_method,
                    "expected_liters": str(expected_liters.quantize(Decimal("0.0001"))),
                    "actual_liters": str(actual_liters),
                    "variance_liters": str(variance_liters),
                    "variance_severity": variance_severity,
                    "fuel_alert_status": fuel_alert_status,
                    "reconciliation_state": reconciliation_state,
                    "policy_snapshot": policy_snapshot,
                    "visibility_level": policy_snapshot["visibility_level"],
                    "cost_display_mode": policy_snapshot["cost_visibility"],
                    "flags": flags,
                    "matching_daily_log_id": getattr(matched_daily_log, "id", None),
                    "alerts_count": len(alerts),
                }
            )

        summary["logs_count"] = len(results)

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
        return {
            "fuel_logs_count": FuelLog.objects.count(),
            "alerts_count": FuelConsumptionAlert.objects.count(),
            "warning_alerts": FuelConsumptionAlert.objects.filter(status=FuelConsumptionAlert.STATUS_WARNING).count(),
            "critical_alerts": FuelConsumptionAlert.objects.filter(status=FuelConsumptionAlert.STATUS_CRITICAL).count(),
            "pending_reconciliation_logs": DailyLog.objects.filter(
                fuel_alert_status__in=[DailyLog.FUEL_ALERT_STATUS_WARNING, DailyLog.FUEL_ALERT_STATUS_CRITICAL]
            ).count(),
            "posted_reconciliations": AuditLog.objects.filter(action="FUEL_RECONCILIATION_POST").count(),
            "calibrated_tanks": TankCalibration.objects.values("asset_id").distinct().count(),
        }
