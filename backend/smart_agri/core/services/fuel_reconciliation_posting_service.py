from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

from smart_agri.core.models.log import DailyLog, FuelConsumptionAlert
from smart_agri.core.services.audit_event_factory import AuditEventFactory
from smart_agri.finance.models import FinancialLedger
from smart_agri.finance.services.core_finance import FinanceService
from smart_agri.inventory.models import FuelLog
from smart_agri.finance.services.farm_finance_authority_service import FarmFinanceAuthorityService


@dataclass(slots=True)
class FuelReconciliationResult:
    farm_id: int
    daily_log_id: int
    fuel_log_id: int
    expected_liters: Decimal
    actual_liters: Decimal
    variance_liters: Decimal
    posted_amount: Decimal
    status: str


class FuelReconciliationPostingService:
    """V7: Upgrade fuel reconciliation from read-model to posted/approved workflow."""

    @staticmethod
    def _assert_reason(reason: str) -> str:
        reason = (reason or "").strip()
        if not reason:
            raise ValueError("سبب التسوية إلزامي ليومية الوقود.")
        return reason

    @staticmethod
    def _sum_expected(alerts: list[FuelConsumptionAlert]) -> Decimal:
        total = Decimal("0.0000")
        for alert in alerts:
            total += Decimal(str(alert.expected_liters or 0))
        return total.quantize(Decimal("0.0001"))

    @staticmethod
    @transaction.atomic
    def approve_and_post(*, user: Any, daily_log_id: int, fuel_log_id: int, reason: str, ref_id: str = "") -> FuelReconciliationResult:
        reason = FuelReconciliationPostingService._assert_reason(reason)

        log = DailyLog.objects.select_for_update().select_related("farm").get(pk=daily_log_id, deleted_at__isnull=True)
        fuel = FuelLog.objects.select_for_update().select_related("farm", "asset_tank").get(pk=fuel_log_id)
        if fuel.farm_id != log.farm_id:
            raise ValueError("يجب أن تكون يومية الوقود ويومية العمل لنفس المزرعة.")

        effective_date = log.log_date or timezone.localdate()
        FinanceService.check_fiscal_period(effective_date, log.farm)
        FarmFinanceAuthorityService.require_profiled_posting_authority(user=user, farm=log.farm, action_label='اعتماد وترحيل تسوية الوقود')

        alerts = list(FuelConsumptionAlert.objects.select_for_update().filter(log_id=log.pk))
        expected = FuelReconciliationPostingService._sum_expected(alerts)
        actual = Decimal(str(fuel.liters_consumed or 0)).quantize(Decimal("0.0001"))
        variance = (actual - expected).quantize(Decimal("0.0001"))

        # Post only if there is any fuel consumption to recognize.
        posted = actual

        ct = ContentType.objects.get_for_model(fuel.__class__)
        common = dict(
            farm=log.farm,
            content_type=ct,
            object_id=str(fuel.pk),
            created_by=user,
            description=f"تسوية وقود يومية: {log.log_date}" + (f" | مرجع: {ref_id}" if ref_id else ""),
            crop_plan=None,
            activity=None,
        )

        # Accounting: Debit fuel expense, Credit fuel inventory.
        if posted > 0:
            FinancialLedger.objects.create(
                account_code=getattr(FinancialLedger, "ACCOUNT_FUEL_EXPENSE", "4010-FUEL-EXP"),
                debit=posted,
                credit=Decimal("0.0000"),
                analytical_tags={"fuel": True, "tank_id": str(fuel.asset_tank_id)},
                **common,
            )
            FinancialLedger.objects.create(
                account_code=getattr(FinancialLedger, "ACCOUNT_FUEL_INVENTORY", "1310-FUEL-INV"),
                debit=Decimal("0.0000"),
                credit=posted,
                analytical_tags={"fuel": True, "tank_id": str(fuel.asset_tank_id)},
                **common,
            )

        # Approve alert state on daily log.
        log.fuel_alert_status = DailyLog.FUEL_ALERT_STATUS_OK
        log.fuel_alert_note = reason
        log.fuel_alert_approved_by = user
        log.fuel_alert_approved_at = timezone.now()
        log.save(update_fields=["fuel_alert_status", "fuel_alert_note", "fuel_alert_approved_by", "fuel_alert_approved_at"])

        event = AuditEventFactory.build(
            actor=user,
            action="FUEL_RECONCILIATION_POST",
            model_name="FuelLog",
            object_id=fuel.pk,
            reason=reason,
            farm_id=log.farm_id,
            source="fuel_reconciliation",
            category="fuel",
            old_value={"expected_liters": str(expected), "alerts": len(alerts)},
            new_value={
                "actual_liters": str(actual),
                "variance_liters": str(variance),
                "posted_amount": str(posted),
                "daily_log_id": log.pk,
                "tank_id": fuel.asset_tank_id,
                "ref_id": ref_id,
            },
        )
        AuditEventFactory.record(event)

        return FuelReconciliationResult(
            farm_id=log.farm_id,
            daily_log_id=log.pk,
            fuel_log_id=fuel.pk,
            expected_liters=expected,
            actual_liters=actual,
            variance_liters=variance,
            posted_amount=posted,
            status="posted",
        )
