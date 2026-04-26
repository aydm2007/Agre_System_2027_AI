from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict

from django.utils import timezone

from smart_agri.core.models.activity import ActivityMachineUsage
from smart_agri.core.models.log import DailyLog, FuelConsumptionAlert


class DieselMonitoringService:
    WARNING_MULTIPLIER = Decimal("1.15")
    CRITICAL_MULTIPLIER = Decimal("1.30")

    PRIORITY = {
        FuelConsumptionAlert.STATUS_OK: 0,
        FuelConsumptionAlert.STATUS_WARNING: 1,
        FuelConsumptionAlert.STATUS_CRITICAL: 2,
    }

    @classmethod
    def evaluate_log(cls, log: DailyLog) -> Dict[str, object]:
        """
        Compare recorded diesel use vs the machine rate benchmark.
        Creates FuelConsumptionAlert rows per asset and returns the overall status/note.
        """
        # mark previous alerts as resolved
        FuelConsumptionAlert.objects.filter(log=log, resolved_at__isnull=True).update(resolved_at=timezone.now())
        usages = ActivityMachineUsage.objects.filter(
            activity__log=log,
            activity__deleted_at__isnull=True,
            activity__asset__isnull=False,
        ).select_related("activity__asset__machine_rate")

        asset_rollup = defaultdict(lambda: {"asset": None, "hours": Decimal("0"), "actual": Decimal("0"), "is_solar_powered": False})

        for usage in usages:
            asset = usage.activity.asset
            if not asset:
                continue
            data = asset_rollup.setdefault(asset.pk, {"asset": asset, "hours": Decimal("0"), "actual": Decimal("0"), "is_solar_powered": False})
            data["asset"] = asset
            hours = Decimal(usage.machine_hours or 0)
            fuel = Decimal(usage.fuel_consumed or 0)
            data["hours"] += hours
            data["actual"] += fuel

        # إضافة الديزل من نشاط الري 
        from smart_agri.core.models.activity import ActivityIrrigation
        irrigations = ActivityIrrigation.objects.filter(
            activity__log=log,
            activity__deleted_at__isnull=True,
            well_asset__isnull=False,
        ).select_related("well_asset__machine_rate")

        for irr in irrigations:
            asset = irr.well_asset
            data = asset_rollup.setdefault(asset.pk, {"asset": asset, "hours": Decimal("0"), "actual": Decimal("0"), "is_solar_powered": False})
            data["asset"] = asset
            fuel = Decimal(irr.diesel_qty or 0)
            data["actual"] += fuel
            if irr.is_solar_powered:
                data["is_solar_powered"] = True

        if not asset_rollup:
            return {
                "status": FuelConsumptionAlert.STATUS_OK,
                "note": "No diesel-consuming assets were logged.",
                "alerts": [],
            }

        alerts: List[FuelConsumptionAlert] = []
        overall_status = FuelConsumptionAlert.STATUS_OK
        note_parts: List[str] = []

        for data in asset_rollup.values():
            asset = data["asset"]
            hours = data["hours"]
            actual = data["actual"]

            machine_rate = getattr(asset, "machine_rate", None)
            fuel_rate = None
            if machine_rate is not None:
                fuel_rate = getattr(machine_rate, "fuel_consumption_rate", None)

            if data.get("is_solar_powered"):
                expected = Decimal("0.0000")
                if actual > 0:
                    status = FuelConsumptionAlert.STATUS_CRITICAL
                    note = f"{asset.name}: تم الإبلاغ عن استهلاك {actual:.4f}L ديزل رغم تفعيل الري بالطاقة الشمسية."
                else:
                    status = FuelConsumptionAlert.STATUS_OK
                    deviation = Decimal("0.00")
                    note = f"{asset.name}: ري بالطاقة الشمسية مطبق، لا يُتوقع استهلاك ديزل."
            elif fuel_rate is None:
                status = FuelConsumptionAlert.STATUS_WARNING
                expected = Decimal("0.0000")
                deviation = Decimal("0.00")
                note = f"{asset.name}: missing fuel consumption benchmark."
            else:
                expected = Decimal("0.0000")
                if hours:
                    expected = (hours * fuel_rate).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
                if expected == 0:
                    status = (
                        FuelConsumptionAlert.STATUS_CRITICAL if actual > 0 else FuelConsumptionAlert.STATUS_OK
                    )
                else:
                    if actual > expected * cls.CRITICAL_MULTIPLIER:
                        status = FuelConsumptionAlert.STATUS_CRITICAL
                    elif actual > expected * cls.WARNING_MULTIPLIER:
                        status = FuelConsumptionAlert.STATUS_WARNING
                    else:
                        status = FuelConsumptionAlert.STATUS_OK

                if expected > 0:
                    from decimal import getcontext
                    deviation = (
                        getcontext().divide(actual - expected, getattr(expected, "value", expected)) * Decimal("100.00")
                    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                else:
                    deviation = Decimal("0.00")

                note = (
                    f"{asset.name}: consumed {actual:.4f}L vs expected {expected:.4f}L "
                    f"(deviation {deviation:+.2f}% | hours {hours:.2f})"
                )

            alerts.append(
                FuelConsumptionAlert.objects.create(
                    log=log,
                    asset=asset,
                    machine_hours=hours.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                    actual_liters=actual.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
                    expected_liters=expected,
                    deviation_pct=deviation,
                    status=status,
                    note=note,
                )
            )

            if status != FuelConsumptionAlert.STATUS_OK:
                note_parts.append(f"{status}: {asset.name} - {note}")

            overall_status = cls._max_status(overall_status, status)

        final_note = "; ".join(note_parts) if note_parts else "Diesel consumption within expected range."

        return {
            "status": overall_status,
            "note": final_note,
            "alerts": alerts,
        }

    @classmethod
    def _max_status(cls, current: str, candidate: str) -> str:
        if cls.PRIORITY.get(candidate, 0) > cls.PRIORITY.get(current, 0):
            return candidate
        return current
