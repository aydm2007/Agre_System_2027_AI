from __future__ import annotations

from smart_agri.core.services.sharecropping_settlement_service import SharecroppingSettlementService
from smart_agri.core.services.sovereign_zakat_service import SovereignZakatService
from smart_agri.finance.services.fiscal_fund_governance_service import FiscalFundGovernanceService


class EnterpriseFinancialReadinessService:
    """Consolidated enterprise finance readiness across fiscal, fund, sovereign, and share settlement."""

    @staticmethod
    def readiness_snapshot(*, period_status: str, is_balanced: bool, has_trace_id: bool, supporting_docs: int, fund_balance, pending_items: int, share_gross_qty, institution_share, partner_share, unit_price, harvest_qty, zakat_rule: str, sovereign_rate=0) -> dict:
        fiscal_packet = FiscalFundGovernanceService.close_packet(
            period_status=period_status,
            is_balanced=is_balanced,
            has_trace_id=has_trace_id,
            supporting_docs=supporting_docs,
            fund_balance=fund_balance,
            pending_items=pending_items,
        )
        share_packet = SharecroppingSettlementService.settle(
            gross_qty=share_gross_qty,
            institution_share=institution_share,
            partner_share=partner_share,
            unit_price=unit_price,
        )
        sovereign_packet = SovereignZakatService.calculate(
            quantity=harvest_qty,
            zakat_rule=zakat_rule,
            unit_cost=unit_price,
            sovereign_rate=sovereign_rate,
        )
        score = 0
        score += 40 if fiscal_packet["close_pack_ready"] else 20
        score += 30 if share_packet["settlement_balanced"] else 10
        score += 30 if sovereign_packet["disclosure_ready"] else 0
        return {
            "fiscal_packet": fiscal_packet,
            "share_packet": share_packet,
            "sovereign_packet": sovereign_packet,
            "financial_readiness_score": score,
        }
