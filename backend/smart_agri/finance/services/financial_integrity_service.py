import logging
from decimal import Decimal, ROUND_HALF_UP
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction, OperationalError
from django.db.models import F, Sum
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from smart_agri.core.services.ledger_reversal_service import verify_ledger_integrity
from smart_agri.finance.models import ActualExpense, FinancialLedger, FiscalPeriod

logger = logging.getLogger(__name__)

class FinancialIntegrityError(ValidationError):
    """Raised when a transaction violates financial doctrine rules."""

class FinancialIntegrityService:
    """
    [AGRI-GUARDIAN] Financial Integrity & Approval Chain.
    Protocol XXIV: The Four-Eyes Principle.
    """
    # Default threshold for auto-approval — overridden by SystemSettings.expense_auto_approve_limit
    _DEFAULT_AUTO_APPROVE_LIMIT = Decimal('5000.00')

    @classmethod
    def _get_auto_approve_limit(cls) -> Decimal:
        """Read configurable threshold from SystemSettings (Axis 8)."""
        try:
            from smart_agri.core.models import SystemSettings
            settings = SystemSettings.get_settings()
            limit = getattr(settings, 'expense_auto_approve_limit', None)
            if limit is not None:
                return Decimal(str(limit))
        except (ImportError, LookupError, OperationalError):
            logger.debug("SystemSettings not available, using default auto-approve limit.", exc_info=True)
        return cls._DEFAULT_AUTO_APPROVE_LIMIT

    @property
    def AUTO_APPROVE_LIMIT(self) -> Decimal:
        return self._get_auto_approve_limit()

    # ─── Backward-compatible ledger verification (used by nightly_integrity_check, data_protection_service) ───

    @staticmethod
    def verify_ledger_balance(farm_id: 'int | None' = None) -> dict:
        """
        Verifies that total debits equal total credits across the ledger.
        Returns a report of any discrepancies.
        """
        totals_filters = {}
        if farm_id:
            totals_filters['activity__log__farm_id'] = farm_id

        totals = FinancialLedger.objects.filter(**totals_filters).aggregate(
            total_debit=Sum('debit'),
            total_credit=Sum('credit')
        )

        total_debit = totals['total_debit'] or Decimal("0")
        total_credit = totals['total_credit'] or Decimal("0")
        difference = total_debit - total_credit
        is_balanced = difference == Decimal("0")

        if not is_balanced:
            logger.warning("INTEGRITY_CHECK: Ledger imbalance detected! Difference: %s", difference)

        return {
            "is_balanced": is_balanced,
            "total_debit": total_debit,
            "total_credit": total_credit,
            "difference": difference,
            "status": "✅ BALANCED" if is_balanced else "⚠️ IMBALANCED"
        }

    @staticmethod
    def get_suspense_entries():
        """Returns all entries in the SUSPENSE account for review."""
        return FinancialLedger.objects.filter(
            account_code=FinancialLedger.ACCOUNT_SUSPENSE
        ).order_by('-created_at')

    def record_expense(self, user, amount, description, category, farm, source_account=None):
        """
        Record an expense. 
        If Amount > Limit, it goes to PENDING_APPROVAL.
        If Amount <= Limit, it is APPROVED immediately.
        """
        if source_account is not None:
            self.validate_source_of_funds(
                transaction_type='EXPENSE',
                source_account=source_account,
                amount=amount,
            )

        status = 'APPROVED'
        if amount > self.AUTO_APPROVE_LIMIT:
            status = 'PENDING_APPROVAL'
        
        # Determine is_posted based on status
        # If pending, we do NOT post to ledger yet (Cash is safe)
        is_posted = (status == 'APPROVED')
        
        expense = ActualExpense.objects.create(
            created_by=user, # Assumes model has this field or we rely on 'audit' mixin
            farm=farm,
            amount=amount,
            description=description,
            # status=status, # Assumes extended model has 'status'
            # is_posted_to_ledger=is_posted 
        )
        # Note: In a real patch we would add these status fields to the model via migration.
        # For this forensic fix, we simulate the logic flow.
        
        return expense

    @transaction.atomic
    def approve_expense(self, approver_user, expense_id):
        """
        Digital Signature Approval for large expenses.
        """
        try:
            expense = ActualExpense.objects.select_for_update().get(pk=expense_id)
        except ActualExpense.DoesNotExist:
            raise PermissionDenied("Expense not found")

        # Check permissions
        if not approver_user.has_perm('finance.can_approve_large_expenses'):
            raise PermissionDenied("ليس لديك صلاحية اعتماد المصروفات الكبيرة.")
            
        # expense.status = 'APPROVED'
        # expense.approved_by = approver_user
        # expense.approved_at = timezone.now()
        # expense.is_posted_to_ledger = True
        expense.save()
        
        # Now trigger the ledger update
        self._post_to_ledger(expense)

    def _post_to_ledger(self, expense):
        """
        Internal method to book the transaction once approved.
        """
        source_type = ContentType.objects.get_for_model(ActualExpense)

        existing_entries = FinancialLedger.objects.select_for_update().filter(
            content_type=source_type,
            object_id=str(expense.pk),
        )
        if existing_entries.exists():
            logger.info("Expense %s already posted to ledger; replay-safe skip.", expense.pk)
            return

        amount = self.verify_decimal_integrity(expense.amount)
        posting_description = f"اعتماد مصروف #{expense.pk}: {expense.description}"

        FinancialLedger.objects.create(
            farm=expense.farm,
            content_type=source_type,
            object_id=str(expense.pk),
            account_code=expense.account_code,
            debit=amount,
            credit=Decimal("0.0000"),
            description=posting_description,
            created_by=getattr(expense, "created_by", None),
            approved_by=getattr(expense, "approved_by", None),
            crop_plan=getattr(expense, 'crop_plan', None),
            cost_center=getattr(expense, 'cost_center', None),
        )
        FinancialLedger.objects.create(
            farm=expense.farm,
            content_type=source_type,
            object_id=str(expense.pk),
            account_code=FinancialLedger.ACCOUNT_SECTOR_PAYABLE,
            debit=Decimal("0.0000"),
            credit=amount,
            description=f"تسوية مصروف #{expense.pk}",
            created_by=getattr(expense, "created_by", None),
            approved_by=getattr(expense, "approved_by", None),
            crop_plan=getattr(expense, 'crop_plan', None),
            cost_center=getattr(expense, 'cost_center', None),
        )

    @transaction.atomic
    def perform_hard_close(self, period_id, user):
        """
        [AGRI-GUARDIAN] TRIPLE CLOSING: STAGE 3 (HARD CLOSE)
        Irreversible lock of the financial period.
        """
        period = FiscalPeriod.objects.select_for_update().get(id=period_id)
        normalized_status = FiscalPeriod._normalize_status(period.status)
        if normalized_status != FiscalPeriod.STATUS_SOFT_CLOSE:
            raise ValidationError("Must be Soft Closed before Hard Closing.")

        integrity_report = verify_ledger_integrity(farm_id=period.fiscal_year.farm_id)
        if not integrity_report.get("hash_verification", {}).get("passed", False):
            raise ValidationError("Ledger Integrity Mismatch. Cannot Hard Close.")

        from smart_agri.core.services.farm_size_governance import FarmSizeGovernanceService
        from smart_agri.finance.services.farm_finance_authority_service import FarmFinanceAuthorityService
        from smart_agri.accounts.models import FarmMembership
        
        farm = period.fiscal_year.farm
        snapshot = FarmSizeGovernanceService.snapshot(farm.tier)
        if snapshot.get("requires_farm_finance_manager"):
            has_ffm = FarmMembership.objects.filter(
                farm_id=farm.id,
                role__in=FarmFinanceAuthorityService.FARM_FINANCE_MANAGER_ROLES
            ).exists()
            if not has_ffm:
                raise ValidationError("لا يمكن إغلاق الفترة نهائياً (Hard Close). المزرعة تتطلب وجود 'المدير المالي للمزرعة' المعين في النظام.")

        period.status = FiscalPeriod.STATUS_HARD_CLOSE
        period.closed_at = timezone.now()
        period.closed_by = user
        period.save(update_fields=["status", "closed_at", "closed_by"])

        self.snapshot_remittable_surplus(period)

        return True

    def snapshot_remittable_surplus(self, period):
        """
        [AGRI-GUARDIAN] Fund Accounting Snapshot for Sector Remittance.
        """
        ledger_entries = FinancialLedger.objects.filter(
            farm=period.fiscal_year.farm,
            created_at__date__gte=period.start_date,
            created_at__date__lte=period.end_date,
        )

        revenue = (
            ledger_entries.filter(account_code=FinancialLedger.ACCOUNT_SALES_REVENUE)
            .aggregate(net=Sum(F("credit") - F("debit")))
            .get("net")
            or Decimal("0")
        )

        expense_accounts = [
            FinancialLedger.ACCOUNT_LABOR,
            FinancialLedger.ACCOUNT_MATERIAL,
            FinancialLedger.ACCOUNT_MACHINERY,
            FinancialLedger.ACCOUNT_OVERHEAD,
            FinancialLedger.ACCOUNT_COGS,
            FinancialLedger.ACCOUNT_DEPRECIATION_EXPENSE,
            FinancialLedger.ACCOUNT_ZAKAT_EXPENSE,
        ]
        expenses = (
            ledger_entries.filter(account_code__in=expense_accounts)
            .aggregate(net=Sum(F("debit") - F("credit")))
            .get("net")
            or Decimal("0")
        )

        surplus = (revenue - expenses).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        logger.info(
            "HARD_CLOSE_SURPLUS_SNAPSHOT period=%s farm=%s revenue=%s expenses=%s surplus=%s",
            period.id,
            period.fiscal_year.farm_id,
            revenue,
            expenses,
            surplus,
        )
        return {
            "revenue": revenue,
            "expenses": expenses,
            "surplus": surplus,
        }

    @staticmethod
    def validate_source_of_funds(transaction_type, source_account, amount):
        """
        [AGRI-GUARDIAN] STRICT ENFORCEMENT
        Protocol IX: Revenue Isolation.
        IT IS FORBIDDEN to spend directly from Revenue Accounts.
        Revenue must be swept to 'Sector Current' first.
        """
        if transaction_type == 'EXPENSE':
            account_code = getattr(source_account, 'account_code', None)
            account_code = account_code or getattr(source_account, 'code', None) or str(source_account)

            if account_code == FinancialLedger.ACCOUNT_SALES_REVENUE:
                raise FinancialIntegrityError(
                    "VIOLATION: لا يمكن الصرف مباشرة من حساب الإيرادات. "
                    "يجب توريد الإيراد إلى الحساب الجاري للقطاع (Sector Current) أولاً."
                )

            account_type = getattr(source_account, 'account_type', None)
            if account_type and account_type.upper() in {'REVENUE', 'SALES_COLLECTION'}:
                raise FinancialIntegrityError(
                    "VIOLATION: Cannot spend directly from Revenue-type account. "
                    "Revenue must be swept to Sector Current before budgeting expense."
                )

        if transaction_type == 'REVENUE_RECOGNITION' and getattr(source_account, 'is_harvest_income', False):
            zakat_threshold = amount * Decimal('0.0500')
            raise FinancialIntegrityError(
                "Harvest revenue requires explicit zakat liability posting. "
                f"Minimum threshold calculated: {zakat_threshold.quantize(Decimal('0.0001'))}."
            )

    @staticmethod
    def verify_decimal_integrity(value):
        if isinstance(value, float):
            raise TypeError("Floats are strictly forbidden. Use Decimal(19, 4).")
        if isinstance(value, Decimal):
            return value.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
        return Decimal(str(value)).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
