import logging
import calendar
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction, models
from django.db.models import Sum, F
from django.conf import settings
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from smart_agri.finance.models import FinancialLedger

logger = logging.getLogger(__name__)

class FinanceService:
    """
    Central Service for Financial Operations and Ledger Integrity.
    Moves financial logic out of Core ActivityService.
    """

    @staticmethod
    def _ensure_open_period(target_date, farm):
        from datetime import date as date_cls
        from smart_agri.finance.models import FiscalYear, FiscalPeriod

        if not target_date or not farm:
            return None
        year = int(target_date.year)
        month = int(target_date.month)
        _, last_day = calendar.monthrange(year, month)

        fiscal_year, _ = FiscalYear.objects.get_or_create(
            farm=farm,
            year=year,
            defaults={
                "start_date": date_cls(year, 1, 1),
                "end_date": date_cls(year, 12, 31),
                "is_closed": False,
            },
        )
        period, _ = FiscalPeriod.objects.get_or_create(
            fiscal_year=fiscal_year,
            month=month,
            defaults={
                "start_date": date_cls(year, month, 1),
                "end_date": date_cls(year, month, last_day),
                "status": FiscalPeriod.STATUS_OPEN,
                "is_closed": False,
            },
        )
        return period

    @staticmethod
    def _latest_period_for_farm(farm):
        from smart_agri.finance.models import FiscalPeriod

        if not farm:
            return None
        return (
            FiscalPeriod.objects.filter(
                fiscal_year__farm=farm,
                deleted_at__isnull=True,
            )
            .select_related("fiscal_year")
            .order_by("-end_date", "-month", "-pk")
            .first()
        )

    @staticmethod
    def check_fiscal_period(date, farm, strict=True):
        """
        Validates that the transaction date falls within an OPEN fiscal period.
        Raises ValidationError if closed.
        """
        from smart_agri.finance.models import FiscalPeriod
        from django.core.exceptions import ValidationError
        
        if not date:
            return

        period = FiscalPeriod.objects.filter(
            fiscal_year__farm=farm,
            start_date__lte=date,
            end_date__gte=date,
            deleted_at__isnull=True
        ).select_related('fiscal_year').first()
        
        if not period:
            auto_create = bool(getattr(settings, "AUTO_CREATE_FISCAL_PERIOD", False))
            latest_period = FinanceService._latest_period_for_farm(farm)
            latest_status = (
                FiscalPeriod._normalize_status(latest_period.status)
                if latest_period is not None
                else None
            )
            can_auto_create = auto_create and latest_period is None

            if strict and auto_create and latest_period is not None and latest_status != FiscalPeriod.STATUS_OPEN:
                raise ValidationError(
                    "Cannot auto-create a fiscal period after a governed close. "
                    f"Latest configured period for farm={farm.id} is "
                    f"{latest_period.fiscal_year.year}-{latest_period.month} ({latest_status})."
                )

            if strict and can_auto_create:
                period = FinanceService._ensure_open_period(date, farm)
            if strict and not period:
                raise ValidationError(
                    f"No fiscal period configured for farm={farm.id} and date={date}."
                )
            if not period:
                return
            
        normalized_status = FiscalPeriod._normalize_status(period.status)
        if normalized_status == FiscalPeriod.STATUS_HARD_CLOSE:
            raise ValidationError(
                "الفترة مغلقة نهائياً. لا يمكن إضافة قيود، يجب استخدام نظام القيود العكسية."
            )
        if strict and normalized_status != FiscalPeriod.STATUS_OPEN:
            raise ValidationError(
                f"Fiscal Period {period.fiscal_year.year}-{period.month} is {normalized_status.upper()}. "
                f"Cannot post transaction for date {date}."
            )
        if period.fiscal_year.is_closed:
             raise ValidationError(
                 f"Fiscal Year {period.fiscal_year.year} is CLOSED. "
                 f"Cannot post transaction for date {date}."
             )

    @staticmethod
    def sync_activity_ledger(activity, user):
        """
        Synchronizes the Financial Ledger with Activity Costs.
        Ensures strict accounting: Debit Material/Cost, Credit Payables/Overhead.
        """
        default_currency = getattr(settings, 'DEFAULT_CURRENCY', 'YER')
        crop_plan = getattr(activity, 'crop_plan', None)
        currency = getattr(crop_plan, 'currency', default_currency) if crop_plan else default_currency
        
        # [FISCAL LOCK]
        effective_date = getattr(activity, 'activity_date', None) or getattr(activity, 'date', None)
        if effective_date and activity.crop_plan:
             FinanceService.check_fiscal_period(effective_date, activity.crop_plan.farm)

        # [AGRI-GUARDIAN] PROTOCOL II: FINANCIAL IMMUTABILITY & CONCURRENCY CONTROL
        with transaction.atomic():
            # Critical Fix: Lock the activity row to serialize access.
            # This prevents two concurrent requests from reading the same 'current_balance' 
            # and posting duplicate entries.
            from smart_agri.core.models.activity import Activity
            from smart_agri.core.models.inventory import BiologicalAssetCohort
            
            # Using select_for_update to lock specifically this row until transaction ends
            activity_locked = Activity.objects.select_for_update().get(pk=activity.pk)
            
            # [AGRI-GUARDIAN Phase 3 - IAS 41 Cost Capitalization]
            # Determine correct expense/asset account base.
            is_wip = False
            first_loc = activity_locked.activity_locations.first()
            loc = first_loc.location if first_loc else None
            if loc and activity_locked.crop:
                filters = {
                    'location': loc,
                    'crop': activity_locked.crop,
                }
                if hasattr(activity_locked, 'crop_variety') and activity_locked.crop_variety:
                    filters['variety'] = activity_locked.crop_variety
                    
                # If we have a JUVENILE or RENEWING cohort, we CAPITALIZE the cost (WIP).
                cohort_qs = BiologicalAssetCohort.objects.filter(
                    **filters, 
                    status__in=[BiologicalAssetCohort.STATUS_JUVENILE, BiologicalAssetCohort.STATUS_RENEWING],
                    deleted_at__isnull=True
                )
                if cohort_qs.exists():
                    is_wip = True
            
            ct = ContentType.objects.get_for_model(activity_locked)
            crop_plan = getattr(activity_locked, 'crop_plan', None)
            
            common_kwargs = dict(
                activity=activity_locked,
                content_type=ct,
                object_id=str(activity_locked.pk),
                created_by=user,
                currency=currency,
                farm=getattr(activity_locked, 'farm', None) or (crop_plan.farm if crop_plan else None),
                crop_plan=crop_plan,
                cost_center=getattr(activity_locked, 'cost_center', None),
            )

            # [Protocol XV] Smart Routing: Distinguish Labor, Material, Machinery, Overhead
            components = [
                ("labor", FinancialLedger.ACCOUNT_WIP if is_wip else FinancialLedger.ACCOUNT_LABOR, FinancialLedger.ACCOUNT_PAYABLE_SALARIES, activity_locked.cost_labor or Decimal("0"), "عمالة"),
                ("material", FinancialLedger.ACCOUNT_WIP if is_wip else FinancialLedger.ACCOUNT_MATERIAL, FinancialLedger.ACCOUNT_INVENTORY_ASSET, activity_locked.cost_materials or Decimal("0"), "مواد"),
                ("machinery", FinancialLedger.ACCOUNT_WIP if is_wip else FinancialLedger.ACCOUNT_MACHINERY, FinancialLedger.ACCOUNT_ACCUM_DEPRECIATION, activity_locked.cost_machinery or Decimal("0"), "آليات"),
                ("overhead", FinancialLedger.ACCOUNT_WIP if is_wip else FinancialLedger.ACCOUNT_OVERHEAD, FinancialLedger.ACCOUNT_PAYABLE_VENDOR, activity_locked.cost_overhead or Decimal("0"), "نفقات عامة"),
                ("wastage", FinancialLedger.ACCOUNT_WASTAGE_EXPENSE, FinancialLedger.ACCOUNT_INVENTORY_ASSET, activity_locked.cost_wastage or Decimal("0"), "هدر تشغيلي"),
            ]

            # 1. Clean up Legacy Entries (entries missing analytical tags) to prevent double accounting
            legacy_balances = FinancialLedger.objects.filter(
                activity=activity_locked
            ).exclude(
                analytical_tags__has_key='cost_component'
            ).exclude(
                # Skip solar depreciation entries which are handled separately below
                description__contains='طاقة شمسية'
            ).values('account_code').annotate(
                net_balance=Sum(F('debit') - F('credit'))
            )
            
            for b in legacy_balances:
                net = b['net_balance'] or Decimal("0")
                if net == 0: continue
                if net > 0:
                    FinancialLedger.objects.create(account_code=b['account_code'], debit=0, credit=net, description=f"قيد عكسي (تصحيح هيكلة قديمة): {activity_locked.pk}", **common_kwargs)
                else:
                    FinancialLedger.objects.create(account_code=b['account_code'], debit=abs(net), credit=0, description=f"قيد عكسي (تصحيح هيكلة قديمة): {activity_locked.pk}", **common_kwargs)

            # 2. Process Smart Routing Deltas per Component
            for comp_key, debit_acct, credit_acct, target_cost, label in components:
                current_balance = FinancialLedger.objects.filter(
                    activity=activity_locked, 
                    account_code=debit_acct,
                    analytical_tags__cost_component=comp_key
                ).aggregate(
                    balance=Sum(F('debit') - F('credit'))
                )['balance'] or Decimal("0")
                
                delta = target_cost - current_balance
                if delta == 0:
                    continue
                    
                comp_tags = {"cost_component": comp_key}
                
                if delta > 0:
                    FinancialLedger.objects.create(
                        account_code=debit_acct, 
                        debit=delta, credit=0,
                        description=f"تسوية تكلفة {label}: نشاط {activity_locked.pk} (+{delta})",
                        analytical_tags=comp_tags,
                        **common_kwargs
                    )
                    FinancialLedger.objects.create(
                        account_code=credit_acct,
                        debit=0, credit=delta,
                        description=f"تسوية التزام {label}: نشاط {activity_locked.pk}",
                        analytical_tags=comp_tags,
                        **common_kwargs
                    )
                elif delta < 0:
                    reversal_amount = abs(delta)
                    FinancialLedger.objects.create(
                        account_code=debit_acct, 
                        debit=0, credit=reversal_amount,
                        description=f"قيد عكسي لتكلفة {label}: نشاط {activity_locked.pk} (-{reversal_amount})",
                        analytical_tags=comp_tags,
                        **common_kwargs
                    )
                    FinancialLedger.objects.create(
                        account_code=credit_acct,
                        debit=reversal_amount, credit=0,
                        description=f"عكس التزام {label}: نشاط {activity_locked.pk}",
                        analytical_tags=comp_tags,
                        **common_kwargs
                    )

            # Phase 6: Solar operational depreciation reserve (hour-based).olar operational depreciation reserve (hour-based).
            solar_dep_target = Decimal("0.0000")
            activity_data = getattr(activity_locked, "data", None) or {}
            if isinstance(activity_data, dict) and activity_data.get("solar_depreciation_cost") is not None:
                solar_dep_target = Decimal(str(activity_data.get("solar_depreciation_cost") or "0"))

            solar_dep_balance = FinancialLedger.objects.filter(
                activity=activity_locked,
                account_code=FinancialLedger.ACCOUNT_DEPRECIATION_EXPENSE,
            ).aggregate(
                balance=Sum(F("debit") - F("credit"))
            )["balance"] or Decimal("0")

            solar_dep_delta = (solar_dep_target - solar_dep_balance).quantize(Decimal("0.0001"))
            if solar_dep_delta != 0:
                if solar_dep_delta > 0:
                    FinancialLedger.objects.create(
                        account_code=FinancialLedger.ACCOUNT_DEPRECIATION_EXPENSE,
                        debit=solar_dep_delta,
                        credit=0,
                        description=f"احتياطي استهلاك تشغيلي للطاقة الشمسية: {activity.pk}",
                        **common_kwargs
                    )
                    FinancialLedger.objects.create(
                        account_code=FinancialLedger.ACCOUNT_ACCUM_DEPRECIATION,
                        debit=0,
                        credit=solar_dep_delta,
                        description=f"استحقاق احتياطي طاقة شمسية: {activity.pk}",
                        **common_kwargs
                    )
                else:
                    reversal_dep = abs(solar_dep_delta)
                    FinancialLedger.objects.create(
                        account_code=FinancialLedger.ACCOUNT_DEPRECIATION_EXPENSE,
                        debit=0,
                        credit=reversal_dep,
                        description=f"قيد عكسي لاستهلاك تشغيلي للطاقة الشمسية: {activity.pk}",
                        **common_kwargs
                    )
                    FinancialLedger.objects.create(
                        account_code=FinancialLedger.ACCOUNT_ACCUM_DEPRECIATION,
                        debit=reversal_dep,
                        credit=0,
                        description=f"قيد عكسي لاستحقاق احتياطي طاقة شمسية: {activity.pk}",
                        **common_kwargs
                    )

    @staticmethod
    def reverse_activity_ledger(activity, user):
        """
        Reverses all financial impact of an activity (e.g. before deletion).
        Uses dynamic balance scanning to properly reverse WIP, Material, Overhead, Depreciation, etc.
        """
        default_currency = getattr(settings, 'DEFAULT_CURRENCY', 'YER')
        crop_plan = getattr(activity, 'crop_plan', None)
        currency = getattr(crop_plan, 'currency', default_currency) if crop_plan else default_currency
        
        with transaction.atomic():
            balances = FinancialLedger.objects.filter(activity=activity).values('account_code').annotate(
                net_balance=Sum(F('debit') - F('credit'))
            )
            
            ct = ContentType.objects.get_for_model(activity)
            crop_plan = getattr(activity, 'crop_plan', None)
            common_kwargs = dict(
                activity=activity,
                content_type=ct,
                object_id=str(activity.pk),
                created_by=user,
                currency=currency,
                farm=getattr(activity, 'farm', None) or (crop_plan.farm if crop_plan else None),
                crop_plan=crop_plan,
                cost_center=getattr(activity, 'cost_center', None),
            )
            
            for b in balances:
                net = b['net_balance'] or Decimal("0")
                if net == 0:
                    continue
                    
                if net > 0:
                    # Debit balance -> Credit to reverse
                    FinancialLedger.objects.create(
                        account_code=b['account_code'], 
                        debit=0,
                        credit=net,
                        description=f"قيد عكسي (إلغاء نشاط): {activity.pk}",
                        **common_kwargs
                    )
                else:
                    # Credit balance -> Debit to reverse
                    FinancialLedger.objects.create(
                        account_code=b['account_code'], 
                        debit=abs(net),
                        credit=0,
                        description=f"قيد عكسي (إلغاء نشاط): {activity.pk}",
                        **common_kwargs
                    )

    # [AGRI-GUARDIAN AUDIT] post_transaction() removed — was dead code referencing
    # non-existent Account/LedgerEntry models from a deprecated architecture.
    # Use sync_activity_ledger() or post_manual_ledger_entry() instead.

    @staticmethod
    def post_manual_ledger_entry(
        farm,
        account_code,
        debit,
        credit,
        description,
        user=None,
        currency=None,
        activity=None,
        cost_center=None,
        crop_plan=None,
        content_type=None,
        object_id=None,
        analytical_tags=None,
    ):
        if debit is None and credit is None:
            raise ValidationError("Either debit or credit must be provided.")
        precision = Decimal("0.0001")
        debit = (
            Decimal(str(debit)).quantize(precision, rounding=ROUND_HALF_UP)
            if debit is not None
            else Decimal("0.0000")
        )
        credit = (
            Decimal(str(credit)).quantize(precision, rounding=ROUND_HALF_UP)
            if credit is not None
            else Decimal("0.0000")
        )
        if (debit > 0 and credit > 0) or (debit == 0 and credit == 0):
            raise ValidationError("Exactly one side must be positive (debit XOR credit).")
        currency = currency or getattr(settings, "DEFAULT_CURRENCY", "YER")
        create_kwargs = dict(
            farm=farm,
            account_code=account_code,
            debit=debit,
            credit=credit,
            description=description,
            created_by=user,
            currency=currency,
            activity=activity,
        )
        if cost_center is not None:
            create_kwargs['cost_center'] = cost_center
        if crop_plan is not None:
            create_kwargs['crop_plan'] = crop_plan
        if content_type is not None:
            create_kwargs['content_type'] = content_type
        if object_id is not None:
            create_kwargs['object_id'] = object_id

        # [AGRI-GUARDIAN §Axis-4] Analytical Purity Enforcement
        # All FinancialLedger rows SHOULD carry cost_center + crop_plan.
        # Log warning when missing to surface analytical gaps without blocking.
        if cost_center is None:
            logger.warning(
                "[ANALYTICAL_PURITY] Ledger entry missing cost_center: "
                "account=%s, farm=%s, desc='%s'",
                account_code, getattr(farm, 'id', farm), description[:80],
            )
        if crop_plan is None:
            logger.warning(
                "[ANALYTICAL_PURITY] Ledger entry missing crop_plan: "
                "account=%s, farm=%s, desc='%s'",
                account_code, getattr(farm, 'id', farm), description[:80],
            )

        if analytical_tags is not None:
            create_kwargs['analytical_tags'] = analytical_tags

        # [AGRI-GUARDIAN Phase 6] Maker-Checker Dual Approval
        # Manual entries are forced to is_posted=False pending Finance approval.
        create_kwargs['is_posted'] = False
        
        return FinancialLedger.objects.create(**create_kwargs)

    @staticmethod
    @transaction.atomic
    def liquidate_payroll_account(
        farm, 
        user, 
        payment_date=None, 
        credit_account=None,
        ref_id="",
        description="",
        advances_recovery_amount=Decimal('0.0000')
    ):
        """
        [AGRI-GUARDIAN Phase 6] Payroll Settlement (End-of-Month)
        Liquidates the Salaries Payable account against Cash/Bank, recovering field advances.
        """
        from smart_agri.finance.models import FinancialLedger
        from django.utils import timezone
        
        payment_date = payment_date or timezone.now().date()
        FinanceService.check_fiscal_period(payment_date, farm)
        
        # Calculate Outstanding Balance for Salaries Payable (What we owe)
        payables = FinancialLedger.objects.filter(
            farm=farm,
            account_code=FinancialLedger.ACCOUNT_PAYABLE_SALARIES,
            is_posted=True
        ).aggregate(balance=Sum(F('credit') - F('debit')))
        
        balance = payables.get('balance') or Decimal('0.0000')
        balance = Decimal(str(balance)).quantize(Decimal('0.0000'), rounding=ROUND_HALF_UP)
        
        if balance <= 0:
            return None # Nothing to liquidate
            
        credit_account = credit_account or FinancialLedger.ACCOUNT_CASH_ON_HAND
        desc = description or (f"تسوية الرواتب والأجور المستحقة - مرجع: {ref_id}" if ref_id else "تسوية الرواتب والأجور المستحقة للفترة")
        
        advances_recovery_amount = Decimal(str(advances_recovery_amount)).quantize(Decimal('0.0000'), rounding=ROUND_HALF_UP)
        
        if advances_recovery_amount > balance:
            raise ValidationError("مبلغ استقطاع السلف يتجاوز إجمالي الرواتب المستحقة.")
            
        net_cash_payout = balance - advances_recovery_amount
        
        entries = []
        
        # 1. Debit Salaries Payable (Closing the Liability)
        entry_debit = FinanceService.post_manual_ledger_entry(
            farm=farm,
            account_code=FinancialLedger.ACCOUNT_PAYABLE_SALARIES,
            debit=balance,
            credit=Decimal('0.0000'),
            description=desc,
            user=user,
        )
        entries.append(entry_debit)
        
        # 2. Credit Advances (Recovering early payouts)
        if advances_recovery_amount > 0:
            entry_advances = FinanceService.post_manual_ledger_entry(
                farm=farm,
                account_code=FinancialLedger.ACCOUNT_RECEIVABLE, # '1200-RECEIVABLE' treats employee advances
                debit=Decimal('0.0000'),
                credit=advances_recovery_amount,
                description=f"استقطاع سلف ميدانية - {desc}",
                user=user,
            )
            entries.append(entry_advances)
            
        # 3. Credit Bank/Cash (Net Cash Outflow)
        if net_cash_payout > 0:
            entry_credit = FinanceService.post_manual_ledger_entry(
                farm=farm,
                account_code=credit_account,
                debit=Decimal('0.0000'),
                credit=net_cash_payout,
                description=f"صافي النقد المدفوع - {desc}",
                user=user,
            )
            entries.append(entry_credit)
        
        return entries
    @staticmethod
    @transaction.atomic
    def settle_labor_liability(farm, user, amount, daily_log=None, description=""):
        """
        [Axis 17] Labor Liability Bridge
        Clears 'Salaries Payable' liability created by DailyLog approval.
        Prevents double-counting expenses when paying worker surrahs via Petty Cash.
        """
        from smart_agri.finance.models import FinancialLedger
        
        # [FISCAL LOCK]
        effective_date = timezone.now().date()
        FinanceService.check_fiscal_period(effective_date, farm)
        
        precision = Decimal("0.0001")
        amount = Decimal(str(amount)).quantize(precision, rounding=ROUND_HALF_UP)
        
        if amount <= 0:
            return None
            
        desc = description or f"تسوية أجور عمالة ميدانية - سجل: {daily_log.pk if daily_log else 'N/A'}"
        
        # [ANALYTICAL PURITY]: Tag as labor settlement for reconciliation radar
        tags = {'settlement_type': 'labor_cash'}
        if daily_log:
            tags['source_log_id'] = daily_log.pk
            
        entry = FinanceService.post_manual_ledger_entry(
            farm=farm,
            account_code=FinancialLedger.ACCOUNT_PAYABLE_SALARIES,
            debit=amount,
            credit=Decimal("0.0000"),
            description=desc,
            user=user,
            analytical_tags=tags,
            activity=None,
        )
        
        return entry
