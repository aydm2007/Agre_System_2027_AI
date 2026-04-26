from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(slots=True)
class FiscalLifecycleDecision:
    can_post: bool
    can_reverse: bool
    can_close: bool
    reason: str
    close_pack_ready: bool


class FiscalFundGovernanceService:
    """Central policy snapshot for fiscal lifecycle and fund accounting controls."""

    @staticmethod
    def evaluate(*, period_status: str, is_balanced: bool, has_trace_id: bool, supporting_docs: int = 0) -> FiscalLifecycleDecision:
        blocked = period_status in {"hard-close", "archived"}
        if blocked:
            return FiscalLifecycleDecision(False, False, False, "الفترة المالية مقفلة إقفالاً نهائيًا.", False)
        if not is_balanced:
            return FiscalLifecycleDecision(False, False, False, "القيد غير متوازن.", False)
        if not has_trace_id:
            return FiscalLifecycleDecision(False, False, False, "trace_id إلزامي لكل حركة مالية مؤسسية.", False)
        close_ready = period_status == "soft-close" and supporting_docs >= 1
        return FiscalLifecycleDecision(True, True, period_status == "soft-close", "ready", close_ready)

    @staticmethod
    def validate_amount(amount) -> Decimal:
        value = Decimal(str(amount or 0)).quantize(Decimal("0.0001"))
        if value < 0:
            raise ValueError("المبالغ السالبة غير مسموحة دون سياسة عكس معتمدة.")
        return value

    @classmethod
    def close_packet(cls, *, period_status: str, is_balanced: bool, has_trace_id: bool, supporting_docs: int, fund_balance, pending_items: int) -> dict:
        decision = cls.evaluate(
            period_status=period_status,
            is_balanced=is_balanced,
            has_trace_id=has_trace_id,
            supporting_docs=supporting_docs,
        )
        balance = cls.validate_amount(fund_balance)
        return {
            "can_post": decision.can_post,
            "can_reverse": decision.can_reverse,
            "can_close": decision.can_close,
            "reason": decision.reason,
            "close_pack_ready": decision.close_pack_ready and pending_items == 0,
            "fund_balance": str(balance),
            "pending_items": pending_items,
        }
