from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from smart_agri.finance.models import FiscalPeriod
from smart_agri.finance.services.financial_integrity_service import FinancialIntegrityService
from smart_agri.finance.services.farm_finance_authority_service import FarmFinanceAuthorityService
from smart_agri.core.services.farm_tiering_policy_service import FarmTieringPolicyService


class FiscalGovernanceService:
    """Service-layer fiscal lifecycle transitions."""

    # [PRD §8.1] Local expense ceiling for SMALL farms (YER).
    # Transactions above this threshold require sector-level review.
    SMALL_FARM_LOCAL_EXPENSE_CEILING = 500_000  # YER

    @staticmethod
    @transaction.atomic
    def transition_period(*, period_id: int, target_status: str, user) -> FiscalPeriod:
        period = FiscalPeriod.objects.select_for_update().get(pk=period_id)
        current_status = FiscalPeriod._normalize_status(period.status)
        target_status = FiscalPeriod._normalize_status(target_status)

        if current_status == target_status:
            raise ValidationError("Period is already in target status")

        allowed_transitions = {
            FiscalPeriod.STATUS_OPEN: {FiscalPeriod.STATUS_SOFT_CLOSE},
            FiscalPeriod.STATUS_SOFT_CLOSE: {FiscalPeriod.STATUS_HARD_CLOSE},
            FiscalPeriod.STATUS_HARD_CLOSE: set(),
        }
        if target_status not in allowed_transitions.get(current_status, set()):
            raise ValidationError(f"Invalid status transition from {current_status} to {target_status}")

        farm = period.farm
        if target_status == FiscalPeriod.STATUS_HARD_CLOSE:
            # [AGRI-GUARDIAN PRD §8.1] SMALL farm compensating control:
            # SMALL farms CANNOT perform hard-close locally.
            # Hard-close must be initiated by sector authority only.
            tier_snap = FarmTieringPolicyService.snapshot(getattr(farm, 'tier', 'small'))
            if tier_snap['tier'] in ('small', 'basic'):
                if not getattr(user, 'is_superuser', False):
                    raise ValidationError(
                        "🔴 [GOVERNANCE BLOCK] المزارع الصغيرة لا يمكنها تنفيذ الإقفال النهائي (Hard Close) محلياً. "
                        "يجب أن يتم الإقفال النهائي من خلال سلطة القطاع. "
                        "[PRD V21 §8.1 — ضوابط تعويضية إلزامية]"
                    )

            FarmFinanceAuthorityService.require_sector_final_authority(user=user, farm=farm, action_label='الإقفال الصارم النهائي')
            FinancialIntegrityService().perform_hard_close(period.id, user)
            
            period = FiscalPeriod.objects.get(pk=period.id)
            
            # [AGRI-GUARDIAN] Phase 8.1 Automated Fiscal Roll-forward
            # If all periods in the fiscal year are now HARD_CLOSED, automatically roll over
            fiscal_year = period.fiscal_year
            active_periods = fiscal_year.periods.exclude(status=FiscalPeriod.STATUS_HARD_CLOSE)
            if not active_periods.exists() and not fiscal_year.is_closed:
                fiscal_year.is_closed = True
                fiscal_year.save(update_fields=['is_closed'])
                from smart_agri.finance.services.fiscal_rollover_service import FiscalYearRolloverService
                FiscalYearRolloverService.rollover_year(
                    fiscal_year_id=fiscal_year.id,
                    user=user
                )
                from smart_agri.core.models.log import AuditLog
                AuditLog.objects.create(
                    user=user,
                    action="AUTOMATED_FISCAL_ROLLOVER",
                    notes=f"Auto-generated next fiscal year and opening balances after closing period {period.id}",
                    farm=farm,
                    remote_ip="0.0.0.0"
                )
                
            return period

        FarmFinanceAuthorityService.require_strict_cycle_authority(user=user, farm=farm, action_label='الإقفال المرحلي للفترة المالية')
        period.status = target_status
        period.closed_at = timezone.now()
        period.closed_by = user
        period.save(update_fields=["status", "is_closed", "closed_at", "closed_by"])
        return period

    @staticmethod
    @transaction.atomic
    def reopen_period(*, period_id: int, user, reason: str) -> FiscalPeriod:
        if not reason or not reason.strip():
            raise ValidationError("A reason is required to reopen a closed period.")
            
        period = FiscalPeriod.objects.select_for_update().get(pk=period_id)
        current_status = FiscalPeriod._normalize_status(period.status)
        
        if current_status == FiscalPeriod.STATUS_OPEN:
            raise ValidationError("Period is already OPEN.")
            
        farm = period.farm
        
        # [AGRI-GUARDIAN] Reopening a closed period is a severe event. Requires sector_final_authority.
        FarmFinanceAuthorityService.require_sector_final_authority(user=user, farm=farm, action_label='إعادة فتح الفترة المحاسبية')
        
        from smart_agri.core.models import AuditLog
        
        period.status = FiscalPeriod.STATUS_OPEN
        period.closed_at = None
        period.closed_by = None
        period._allow_reopen = True
        
        period.save(update_fields=["status", "is_closed", "closed_at", "closed_by"])
        
        AuditLog.objects.create(
            user=user,
            action="FISCAL_PERIOD_REOPEN",
            notes=f"Reopened fiscal period {period_id}. Reason: {reason.strip()}",
            farm=farm,
            remote_ip="0.0.0.0"
        )
        return period
