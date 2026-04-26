import uuid
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType

from smart_agri.finance.models_petty_cash import PettyCashRequest, PettyCashSettlement, PettyCashLine
from smart_agri.finance.models_treasury import CashBox, TreasuryTransaction
from smart_agri.finance.models import FinancialLedger
from smart_agri.core.models.settings import FarmSettings
from smart_agri.core.services.sensitive_audit import audit_financial_mutation, log_sensitive_mutation
from smart_agri.finance.services.farm_finance_authority_service import FarmFinanceAuthorityService
from smart_agri.core.decorators import enforce_strict_mode

class PettyCashService:
    """
    [AGRI-GUARDIAN Phase 13] Petty Cash Management Service.
    Handles disbursement (issuing cash to employee) and settlement (submitting receipts).
    """

    @staticmethod
    def _module_enabled(farm) -> bool:
        farm_settings = FarmSettings.objects.filter(farm=farm).first()
        if not farm_settings or farm_settings.mode != FarmSettings.MODE_STRICT:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("🔴 [FORENSIC BLOCK] Service execution blocked: STRICT mode required.")
        return farm_settings.enable_petty_cash

    @staticmethod
    @transaction.atomic
    def create_request(*, user, farm, amount, description, cost_center=None) -> PettyCashRequest:
        enforce_strict_mode(farm)
        if not PettyCashService._module_enabled(farm):
            raise ValidationError("Petty Cash module is disabled for this farm.")

        # [AGRI-GUARDIAN] Phase 8.2 Proactive Custody Limits Alerting
        farm_settings = FarmSettings.objects.filter(farm=farm).first()
        max_limit = Decimal(str(getattr(farm_settings, 'max_petty_cash_custody_limit', '15000.00')))
        
        # Calculate existing active custody
        active_requests = PettyCashRequest.objects.filter(
            farm=farm,
            requester=user,
            status__in=[
                PettyCashRequest.STATUS_PENDING,
                PettyCashRequest.STATUS_APPROVED,
                PettyCashRequest.STATUS_DISBURSED
            ]
        )
        existing_custody = sum((req.amount for req in active_requests), Decimal("0.00"))
        
        if existing_custody + amount > max_limit:
            from smart_agri.core.models.log import AuditLog
            msg = f"تهديد أمني: المستخدم تجاوز الحد الأقصى للعهدة ({max_limit}). العهدة الحالية: {existing_custody}, المطلوبة: {amount}"
            AuditLog.objects.create(
                user=user,
                action="PROACTIVE_PETTY_CASH_WARNING",
                notes=msg,
                farm=farm,
                remote_ip="0.0.0.0"
            )
            raise ValidationError(f"لا يمكن إنشاء الطلب. إجمالي العهدة النشطة سيتجاوز الحد الأقصى المسموح به وهو {max_limit}.")

        request_obj = PettyCashRequest(
            farm=farm,
            requester=user,
            amount=amount,
            description=(description or "").strip(),
            cost_center=cost_center,
        )
        request_obj.full_clean()
        request_obj.save()

        audit_financial_mutation(
            actor=user,
            action="CREATE",
            model_name="PettyCashRequest",
            object_id=request_obj.pk,
            farm_id=request_obj.farm_id,
            amount=request_obj.amount,
            description=f"Create petty cash request #{request_obj.pk}",
            new_state={
                "status": request_obj.status,
                "description": request_obj.description,
                "cost_center": request_obj.cost_center_id,
            },
        )
        return request_obj

    @staticmethod
    @transaction.atomic
    def approve_request(request_id: int, user) -> PettyCashRequest:
        req = PettyCashRequest.objects.select_for_update().select_related("farm").get(id=request_id)

        if not PettyCashService._module_enabled(req.farm):
            raise ValidationError("Petty Cash module is disabled for this farm.")
        if req.status != PettyCashRequest.STATUS_PENDING:
            raise ValidationError(f"Request must be PENDING to approve. Current status: {req.status}")
        FarmFinanceAuthorityService.require_profiled_posting_authority(user=user, farm=req.farm, action_label='اعتماد طلب عهدة')

        # [AGRI-GUARDIAN Phase 6] Maker-Checker
        if req.requester_id == user.id:
            raise ValidationError("⚠️ [GOVERNANCE BLOCK] الفصل في المهام: الموظف طالب العهدة لا يمكنه اعتماد طلب العهدة لنفسه.")


        previous_status = req.status
        req.status = PettyCashRequest.STATUS_APPROVED
        req.approved_by = user
        req.approved_at = timezone.now()
        req.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])

        log_sensitive_mutation(
            actor=user,
            action="APPROVE",
            model_name="PettyCashRequest",
            object_id=req.pk,
            farm_id=req.farm_id,
            reason=f"Approved petty cash request #{req.pk}",
            old_value={"status": previous_status},
            new_value={"status": req.status, "approved_by": getattr(user, "pk", None)},
        )
        return req

    @staticmethod
    @transaction.atomic
    def create_settlement(*, request_id: int, user, approval_note: str = "") -> PettyCashSettlement:
        req = PettyCashRequest.objects.select_for_update().select_related("farm").get(id=request_id)

        if not PettyCashService._module_enabled(req.farm):
            raise ValidationError("Petty Cash module is disabled for this farm.")
        if req.status != PettyCashRequest.STATUS_DISBURSED:
            raise ValidationError("Petty cash request must be DISBURSED before opening a settlement.")
        if hasattr(req, "settlement"):
            raise ValidationError("A settlement already exists for this petty cash request.")

        settlement = PettyCashSettlement(
            request=req,
            approval_note=(approval_note or "").strip() or None,
        )
        settlement.full_clean()
        settlement.save()

        log_sensitive_mutation(
            actor=user,
            action="CREATE",
            model_name="PettyCashSettlement",
            object_id=settlement.pk,
            farm_id=req.farm_id,
            reason=f"Created petty cash settlement #{settlement.pk} for request #{req.pk}",
            old_value=None,
            new_value={"status": settlement.status, "request_id": req.pk},
        )
        return settlement

    @staticmethod
    @transaction.atomic
    def add_settlement_line(*, settlement_id: int, user, amount, description, date=None, budget_classification=None) -> PettyCashLine:
        settlement = (
            PettyCashSettlement.objects.select_for_update()
            .select_related("request", "request__farm")
            .get(id=settlement_id)
        )

        if not PettyCashService._module_enabled(settlement.request.farm):
            raise ValidationError("Petty Cash module is disabled for this farm.")
        if settlement.status != PettyCashSettlement.STATUS_PENDING:
            raise ValidationError("Cannot add lines to a posted settlement.")

        line = PettyCashLine(
            settlement=settlement,
            amount=amount,
            description=(description or "").strip(),
            date=date or timezone.localdate(),
            budget_classification=budget_classification,
        )
        line.full_clean()
        line.save()

        total_expenses = sum(
            (existing.amount for existing in settlement.lines.filter(deleted_at__isnull=True)),
            Decimal("0.0000"),
        )
        refund_amount = (settlement.request.amount - total_expenses).quantize(Decimal("0.0001"))
        settlement.total_expenses = total_expenses
        settlement.refund_amount = refund_amount
        settlement.full_clean()
        settlement.save(update_fields=["total_expenses", "refund_amount", "updated_at"])

        audit_financial_mutation(
            actor=user,
            action="CREATE",
            model_name="PettyCashLine",
            object_id=line.pk,
            farm_id=settlement.request.farm_id,
            amount=line.amount,
            description=f"Add petty cash line #{line.pk} to settlement #{settlement.pk}",
            new_state={
                "settlement_id": settlement.pk,
                "description": line.description,
                "budget_classification": line.budget_classification_id,
                "settlement_total_expenses": str(settlement.total_expenses),
                "settlement_refund_amount": str(settlement.refund_amount),
            },
        )
        return line


    @staticmethod
    @transaction.atomic
    def disburse_request(request_id: int, cash_box_id: int, user) -> PettyCashRequest:
        """
        Disburse an approved petty cash request.
        Creates a TreasuryTransaction (CashBox outflow) and a Suspense Ledger entry.
        """
        req = PettyCashRequest.objects.select_for_update().get(id=request_id)
        enforce_strict_mode(req.farm)
        
        # 1. Check Module Toggle
        farm_settings = FarmSettings.objects.filter(farm=req.farm).first()
        if farm_settings and not farm_settings.enable_petty_cash:
            raise ValidationError("Petty Cash module is disabled for this farm.")

        # 2. State Guard
        if req.status != PettyCashRequest.STATUS_APPROVED:
            raise ValidationError(f"Request must be APPROVED to disburse. Current status: {req.status}")
        FarmFinanceAuthorityService.require_profiled_posting_authority(user=user, farm=req.farm, action_label='صرف عهدة نقدية')

        # 3. Create Treasury Transaction (Cash Outflow)
        idempotency_key = f"pc_disburse_{req.id}_{uuid.uuid4().hex[:8]}"
        
        treasury_tx = TreasuryTransaction(
            farm=req.farm,
            cash_box_id=cash_box_id,
            transaction_type=TreasuryTransaction.EXPENSE,
            amount=req.amount,
            reference=f"Disbursement for PC Request #{req.id}",
            note=req.description,
            cost_center=req.cost_center,
            idempotency_key=idempotency_key,
            created_by=user,
            party=req.requester
        )
        # TreasuryTransaction.save() will handle CashBox deduction and its own atomic lock.
        treasury_tx.save()

        # 4. Generate Ledger Entries
        # Debit: Suspense Account (Temporary Custody/Liability on Employee)
        # Credit: Cash on Hand (Main Safe/Bank - Handled implicitly by Treasury or we log explicitly?)
        # Let's log the explicit double-entry for the Suspense portion so it balances.
        # Actually, TreasuryTransaction already implies a credit to Cash. We just need the Ledger entries to reflect it.
        
        # Credit Cash Account
        ledger_credit = FinancialLedger(
            farm=req.farm,
            account_code=FinancialLedger.ACCOUNT_CASH_ON_HAND,
            credit=req.amount,
            debit=Decimal("0.0000"),
            description=f"Issue Petty Cash #{req.id}",
            transaction_source=treasury_tx,
            created_by=user,
            cost_center=req.cost_center,
            entity=req.requester
        )
        ledger_credit.save()

        # Debit Suspense Account
        ledger_debit = FinancialLedger(
            farm=req.farm,
            account_code=FinancialLedger.ACCOUNT_SUSPENSE,
            credit=Decimal("0.0000"),
            debit=req.amount,
            description=f"Custody for Petty Cash #{req.id}",
            transaction_source=req,
            created_by=user,
            cost_center=req.cost_center,
            entity=req.requester
        )
        ledger_debit.save()

        # 5. Update Request State
        req.status = PettyCashRequest.STATUS_DISBURSED
        req.disbursed_transaction = treasury_tx
        req.save(update_fields=['status', 'disbursed_transaction', 'updated_at'])

        return req

    @staticmethod
    @transaction.atomic
    def settle_request(settlement_id: int, user) -> PettyCashSettlement:
        """
        Approve and post a Petty Cash Settlement.
        Reverses the Suspense account and books actual expenses.
        """
        settlement = PettyCashSettlement.objects.select_for_update().get(id=settlement_id)
        req = settlement.request
        enforce_strict_mode(req.farm)

        # 1. Check Module Toggle
        farm_settings = FarmSettings.objects.filter(farm=req.farm).first()
        if farm_settings and not farm_settings.enable_petty_cash:
            raise ValidationError("Petty Cash module is disabled for this farm.")

        # 2. State Guard
        if settlement.status != PettyCashSettlement.STATUS_PENDING:
            raise ValidationError(f"Settlement must be PENDING. Current: {settlement.status}")
        FarmFinanceAuthorityService.require_profiled_posting_authority(user=user, farm=req.farm, action_label='اعتماد تسوية عهدة')
        
        if req.status != PettyCashRequest.STATUS_DISBURSED:
            raise ValidationError("Original request must be DISBURSED before it can be settled.")

        # [AGRI-GUARDIAN Phase 6] Maker-Checker
        if req.requester_id == user.id:
            raise ValidationError("⚠️ [GOVERNANCE BLOCK] الفصل في المهام: الموظف صاحب العهدة لا يمكنه اعتماد التسوية النهائية لنفسه.")


        # [AGRI-GUARDIAN Axis 12] Enforce Attachment Governance for STRICT mode
        if farm_settings and getattr(farm_settings, 'mode', FarmSettings.MODE_SIMPLE) == FarmSettings.MODE_STRICT:
            if getattr(farm_settings, 'mandatory_attachment_for_cash', True):
                from smart_agri.core.models.log import Attachment
                has_attachment = Attachment.objects.filter(
                    farm_id=req.farm_id,
                    related_document_type__in=["petty_cash_request", "petty_cash_settlement"],
                    document_scope__in=[str(req.id), str(settlement.id)]
                ).exclude(malware_scan_status=Attachment.MALWARE_SCAN_QUARANTINED).exists()
                if not has_attachment:
                    raise ValidationError("🔴 [GOVERNANCE BLOCK] يتطلب الاعتماد النهائي في المود الصارم وجود مرفق سليم (غير محجور) يدعم الدفعة/التسوية.")


        # Recalculate expenses
        lines = list(settlement.lines.all())
        total_expenses = sum(line.amount for line in lines)
        if total_expenses != settlement.total_expenses:
            settlement.total_expenses = total_expenses

        # Refund is the difference
        expected_refund = req.amount - total_expenses
        if settlement.refund_amount != expected_refund:
             # Just set it, normally UI does this but we enforce
             settlement.refund_amount = expected_refund

        if settlement.refund_amount < 0:
             raise ValidationError("Total expenses exceed the requested amount. The employee must request additional funds separately.")

        # 3. Ledger Entries: Reverse Suspense
        # We need to Credit Suspense for the FULL original disbursed amount to clear it.
        ledger_clear_suspense = FinancialLedger(
            farm=req.farm,
            account_code=FinancialLedger.ACCOUNT_SUSPENSE,
            credit=req.amount,
            debit=Decimal("0.0000"),
            description=f"Clear Custody PC #{req.id}",
            transaction_source=settlement,
            created_by=user,
            cost_center=req.cost_center,
            entity=req.requester
        )
        ledger_clear_suspense.save()

        # Debit Actual Expenses or Liabilities based on lines [Axis 17 Bridge]
        from smart_agri.finance.services.core_finance import FinanceService

        for line in lines:
            if getattr(line, 'is_labor_settlement', False) and line.related_daily_log:
                # [SOVEREIGN BRIDGE]: Specialized logic to clear existing labor liability
                # instead of booking a new expense (prevents double-counting).
                FinanceService.settle_labor_liability(
                    farm=req.farm,
                    user=user,
                    amount=line.amount,
                    daily_log=line.related_daily_log,
                    description=f"PC Labor Pay: {line.description[:100]}"
                )
            else:
                # Standard administrative expense posting
                acc_code = FinancialLedger.ACCOUNT_EXPENSE_ADMIN
                
                # Future mapping could happen here if BudgetClass overrides the account
                
                ledger_exp = FinancialLedger(
                    farm=req.farm,
                    account_code=acc_code,
                    credit=Decimal("0.0000"),
                    debit=line.amount,
                    description=f"PC Exp: {line.description[:100]}",
                    transaction_source=line,
                    created_by=user,
                    cost_center=req.cost_center,
                    entity=req.requester
                )
                ledger_exp.save()

        # If there is a refund, Debit Cash on Hand (returning money to the safe)
        if settlement.refund_amount > 0:
            # Note: We should ideally create a TreasuryTransaction RECEIPT for the refund cash returning to CashBox.
            # But the user might not return it to the exact same cash box immediately. 
            # Assuming returning to Master Safe or same box.
            if req.disbursed_transaction:
                return_box_id = req.disbursed_transaction.cash_box_id
            else:
                return_box_id = CashBox.objects.filter(farm=req.farm, is_active=True).first().id
                
            idempotency_key = f"pc_refund_{settlement.id}_{uuid.uuid4().hex[:8]}"
            treasury_tx = TreasuryTransaction(
                farm=req.farm,
                cash_box_id=return_box_id,
                transaction_type=TreasuryTransaction.RECEIPT,
                amount=settlement.refund_amount,
                reference=f"Refund from PC #{req.id}",
                note="Remaining unspent custody returned",
                cost_center=req.cost_center,
                idempotency_key=idempotency_key,
                created_by=user,
                party=req.requester
            )
            treasury_tx.save()
            
            ledger_refund = FinancialLedger(
                farm=req.farm,
                account_code=FinancialLedger.ACCOUNT_CASH_ON_HAND,
                credit=Decimal("0.0000"),
                debit=settlement.refund_amount,
                description=f"Refund PC #{req.id}",
                transaction_source=treasury_tx,
                created_by=user,
                cost_center=req.cost_center,
                entity=req.requester
            )
            ledger_refund.save()

        # 4. Update States
        settlement.status = PettyCashSettlement.STATUS_APPROVED
        settlement.settled_by = user
        settlement.settled_at = timezone.now()
        settlement.save(update_fields=['status', 'settled_by', 'settled_at', 'total_expenses', 'refund_amount', 'updated_at'])

        req.status = PettyCashRequest.STATUS_SETTLED
        req.save(update_fields=['status', 'updated_at'])

        return settlement
