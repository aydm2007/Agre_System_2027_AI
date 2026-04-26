from __future__ import annotations

from smart_agri.core.services.farm_tiering_policy_service import FarmTieringPolicyService
from smart_agri.core.services.harvest_compliance_service import HarvestComplianceService
from smart_agri.core.services.schedule_variance_service import ScheduleVarianceService
from smart_agri.core.services.seasonal_settlement_service import SeasonalSettlementService


class PlanningEnterpriseService:
    """Enterprise planning orchestration: plan variance + seasonal closure + harvest readiness."""

    @staticmethod
    def readiness_snapshot(*, tier: str, approvals_count: int, delegated_roles: int, wip_cost, harvested_cost, carry_forward_cost, expected_revenue, location_id, crop_plan_id, gross_qty, attachments_count: int, lot_code: str) -> dict:
        tier_ok = FarmTieringPolicyService.is_enterprise_ready(tier, approvals_count=approvals_count, delegated_roles=delegated_roles)
        close_packet = SeasonalSettlementService.close_packet(
            wip_cost=wip_cost,
            harvested_cost=harvested_cost,
            carry_forward_cost=carry_forward_cost,
            expected_revenue=expected_revenue,
            approvals_count=approvals_count,
        )
        harvest_packet = HarvestComplianceService.validate(
            location_id=location_id,
            crop_plan_id=crop_plan_id,
            gross_qty=gross_qty,
            attachments_count=attachments_count,
            require_attachment=True,
            lot_code=lot_code,
        )
        score = 0
        score += 35 if tier_ok else 0
        score += 35 if close_packet["ready_for_close"] else 20
        score += 30 if harvest_packet["quarantine_release_ready"] else 0
        return {
            "tier_ready": tier_ok,
            "close_packet": close_packet,
            "harvest_packet": harvest_packet,
            "planning_readiness_score": score,
        }

    @staticmethod
    def variance_probe(*, activity, user=None) -> dict | None:
        return ScheduleVarianceService.check_schedule_variance(activity=activity, user=user)
