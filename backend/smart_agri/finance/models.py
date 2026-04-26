from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid
import hashlib
from datetime import date
from django.conf import settings
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from smart_agri.core.models.rls_scope import get_rls_user_id

# Base Model Import
from smart_agri.core.models.base import SoftDeleteModel

# NOTE: SalesInvoice and Customer have been moved to 'smart_agri.sales'.

class CostConfiguration(SoftDeleteModel):
    SUPPORTED_CURRENCIES = [
        ('YER', 'Yemeni Rial'),
        ('SAR', 'Saudi Riyal'),
    ]
    
    farm = models.OneToOneField(
        'core.Farm',
        on_delete=models.CASCADE,
        related_name='cost_config_new'
    )
    overhead_rate_per_hectare = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        default=Decimal("50.0000"),
        help_text="معدل تكلفة النفقات العامة لكل هكتار (ريال يمني - دقة عالية)"
    )
    variance_warning_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("10.00"),
        help_text="حد التحذير للانحراف كنسبة مئوية من الميزانية"
    )
    variance_critical_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("20.00"),
        help_text="حد الانحراف الحرج كنسبة مئوية من الميزانية"
    )
    currency = models.CharField(max_length=3, choices=SUPPORTED_CURRENCIES, default="YER")
    effective_date = models.DateField(default=date.today)

    class Meta:
        managed = True
        db_table = 'core_costconfiguration' # Safe-Move
        ordering = ['-effective_date', '-id']
        verbose_name = "إعداد التكاليف"
        verbose_name_plural = "إعدادات التكاليف"

    def clean(self):
        super().clean()
        if self.overhead_rate_per_hectare is not None and self.overhead_rate_per_hectare < 0:
            raise ValidationError({
                'overhead_rate_per_hectare': 'معدل النفقات العامة لا يمكن أن يكون سالباً.'
            })

class BudgetClassification(models.Model):
    """
    دليل بنود الموازنة (الباب الأول، الثاني، الخ)
    Code: 2111 (Fuel), 3112 (Maintenance)
    """
    code = models.CharField(max_length=20, unique=True)
    name_ar = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    class Meta:
        managed = True
        db_table = 'core_budgetclassification'
        ordering = ['code']
        verbose_name = "بند الموازنة"
        verbose_name_plural = "بنود الموازنة"

    def __str__(self):
        return f"{self.code} - {self.name_ar}"


class SectorRelationship(models.Model):
    """
    Tracks debt/credit with the Headquarters (HQ).
    """
    farm = models.OneToOneField('core.Farm', on_delete=models.PROTECT)
    current_balance = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        default=0,
        help_text="الرصيد مع الإدارة العامة"
    )
    allow_revenue_recycling = models.BooleanField(
        default=False,
        help_text="هل يسمح بتدوير الإيراد دون توريد؟"
    )

    class Meta:
        managed = True
        db_table = 'core_sectorrelationship'
        verbose_name = "علاقة القطاع"
        verbose_name_plural = "علاقات القطاع"

    def __str__(self):
        return f"{self.farm} - {self.current_balance}"

class CostCenter(SoftDeleteModel):
    """
    البعد التحليلي لمراكز التكلفة (Analytical Dimension)
    يستخدم لتجنب تضخم شجرة الحسابات (Multi-Dimensional Ledger).
    مثال: "مزرعة المانجو قطاع أ"، "ورشة الصيانة"، "فرقة العمال 1".
    """
    farm = models.ForeignKey(
        'core.Farm',
        on_delete=models.CASCADE,
        related_name='cost_centers',
        help_text="المزرعة التابع لها مركز التكلفة (Mandatory RLS)"
    )
    code = models.CharField(max_length=50, db_index=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        managed = True
        db_table = 'finance_costcenter'
        ordering = ['farm', 'code']
        verbose_name = "مركز تكلفة"
        verbose_name_plural = "مراكز التكلفة"
        constraints = [
            models.UniqueConstraint(
                fields=['farm', 'code'],
                condition=models.Q(deleted_at__isnull=True),
                name='uq_costcenter_farm_code_active'
            )
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

class FinancialLedger(models.Model):
    """
    سجل مالي غير قابل للتغيير لـ AgriAsset.
    """
    class ScopedManager(models.Manager):
        def get_queryset(self):
            qs = super().get_queryset()
            user_id = get_rls_user_id()
            if user_id is None or user_id == -1:
                return qs
            return qs.filter(
                Q(farm__memberships__user_id=user_id)
                | Q(farm__isnull=True, activity__activity_locations__location__farm__memberships__user_id=user_id)
                | Q(farm__isnull=True, crop_plan__farm__memberships__user_id=user_id)
            ).distinct()

    def __init__(self, *args, **kwargs):
        legacy_amount = kwargs.pop("amount", None)
        legacy_transaction_type = kwargs.pop("transaction_type", None)
        if legacy_amount is not None:
            if legacy_transaction_type == "CREDIT":
                kwargs.setdefault("credit", legacy_amount)
                kwargs.setdefault("debit", Decimal("0"))
            else:
                kwargs.setdefault("debit", legacy_amount)
                kwargs.setdefault("credit", Decimal("0"))
        if not args:
            kwargs.setdefault("account_code", FinancialLedger.ACCOUNT_MATERIAL)
            kwargs.setdefault("description", "Legacy Ledger Entry")
        super().__init__(*args, **kwargs)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # String Refs
    activity = models.ForeignKey('core.Activity', on_delete=models.PROTECT, related_name='ledger_entries_new', null=True, blank=True)
    crop_plan = models.ForeignKey("core.CropPlan", on_delete=models.PROTECT, related_name='ledger_entries_new', null=True, blank=True)

    # [AGRI-GUARDIAN] ARCHITECTURAL DECOUPLING
    # Generic Relation to allow linking to ANY transaction source (Activity, Sale, InventoryAdjustment)
    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT, null=True, blank=True)
    object_id = models.CharField(max_length=36, null=True, blank=True) # Supports UUID or ID
    transaction_source = GenericForeignKey('content_type', 'object_id')

    # [AGRI-GUARDIAN] Analytical dimension: counterparty / entity (Vendor, Employee, Customer, etc.)
    entity_content_type = models.ForeignKey(
        ContentType, on_delete=models.PROTECT, null=True, blank=True, related_name='ledger_entities_new'
    )
    entity_object_id = models.CharField(max_length=36, null=True, blank=True)
    entity = GenericForeignKey('entity_content_type', 'entity_object_id')

    
    # [AGRI-GUARDIAN] IMPROVEMENT: Direct Farm Reference for Strict Isolation
    farm = models.ForeignKey("core.Farm", on_delete=models.PROTECT, related_name='ledger_entries_new', null=True, blank=True)

    # [AGRI-GUARDIAN] Analytical Dimensions (Ultimate Edition)
    cost_center = models.ForeignKey(
        'finance.CostCenter', 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True,
        related_name='ledger_entries_new',
        help_text="مركز التكلفة التحليلي (Dimension 1)"
    )
    analytical_tags = models.JSONField(
        default=dict, 
        blank=True, 
        help_text="وسوم تحليلية إضافية (مثل: دورة المحصول، المعدة، الخ)"
    )

    # Treasury / cash management accounts
    ACCOUNT_CASH_ON_HAND = '1100-CASH'
    ACCOUNT_BANK = '1110-BANK'
    ACCOUNT_PAYABLE_VENDOR = '2001-PAY-VENDOR'
    ACCOUNT_EXPENSE_ADMIN = '4001-EXP-ADMIN'
    ACCOUNT_RENT_EXPENSE = '2200-RENT-EXP'
    ACCOUNT_EXP_ELEC = 'EXP-ELEC'


    ACCOUNT_LABOR = '1000-LABOR'
    ACCOUNT_MATERIAL = '2000-MATERIAL'
    ACCOUNT_MACHINERY = '3000-MACHINERY'
    ACCOUNT_OVERHEAD = '4000-OVERHEAD'
    ACCOUNT_SALES_REVENUE = '5000-REVENUE'
    ACCOUNT_RECEIVABLE = '1200-RECEIVABLE'
    ACCOUNT_INVENTORY_ASSET = '1300-INV-ASSET'
    ACCOUNT_COGS = '6000-COGS'
    ACCOUNT_WIP = '1400-WIP'
    ACCOUNT_DEPRECIATION_EXPENSE = '7000-DEP-EXP'
    ACCOUNT_ACCUM_DEPRECIATION = '1500-ACC-DEP'
    ACCOUNT_FIXED_ASSET = '1600-FIXED-ASSET'
    ACCOUNT_FUEL_EXPENSE = '4010-FUEL-EXP'
    ACCOUNT_WASTAGE_EXPENSE = '4015-WASTAGE-EXP'
    ACCOUNT_FUEL_INVENTORY = '1310-FUEL-INV'
    ACCOUNT_ASSET_DISPOSAL_GAIN = '7201-ASSET-GAIN'
    ACCOUNT_ASSET_DISPOSAL_LOSS = '7202-ASSET-LOSS'
    ACCOUNT_PAYABLE_SALARIES = '2000-PAY-SAL'
    ACCOUNT_ACCRUED_LIABILITY = '2100-ACCRUED-LIABILITY'
    ACCOUNT_SECTOR_PAYABLE = '2100-SECTOR-PAY'
    ACCOUNT_ZAKAT_EXPENSE = '7100-ZAKAT-EXP'
    ACCOUNT_ZAKAT_PAYABLE = '2105-ZAKAT-PAY'
    ACCOUNT_VAT_PAYABLE = '2110-VAT-PAY'
    ACCOUNT_SUSPENSE = '9999-SUSPENSE'

    ACCOUNT_CHOICES = [
        (ACCOUNT_CASH_ON_HAND, 'Cash on Hand'),
        (ACCOUNT_BANK, 'Bank'),
        (ACCOUNT_PAYABLE_VENDOR, 'Vendor Payable'),
        (ACCOUNT_EXPENSE_ADMIN, 'Admin / Petty Cash Expense'),
        (ACCOUNT_RENT_EXPENSE, 'Rent Expense'),
        (ACCOUNT_EXP_ELEC, 'Electricity Expense'),
        (ACCOUNT_LABOR, 'Labor Cost'),
        (ACCOUNT_MATERIAL, 'Material Cost'),
        (ACCOUNT_MACHINERY, 'Machinery Cost'),
        (ACCOUNT_OVERHEAD, 'Overhead Cost'),
        (ACCOUNT_SALES_REVENUE, 'Sales Revenue'),
        (ACCOUNT_RECEIVABLE, 'Accounts Receivable'),
        (ACCOUNT_INVENTORY_ASSET, 'Inventory Asset'),
        (ACCOUNT_COGS, 'Cost of Goods Sold'),
        (ACCOUNT_WIP, 'Work In Progress'),
        (ACCOUNT_DEPRECIATION_EXPENSE, 'Depreciation Expense'),
        (ACCOUNT_ACCUM_DEPRECIATION, 'Accumulated Depreciation'),
        (ACCOUNT_FIXED_ASSET, 'Fixed Assets'),
          (ACCOUNT_FUEL_INVENTORY, 'Fuel Inventory'),
          (ACCOUNT_FUEL_EXPENSE, 'Fuel Expense'),
          (ACCOUNT_WASTAGE_EXPENSE, 'Operational Wastage Expense'),
          (ACCOUNT_ASSET_DISPOSAL_GAIN, 'Asset Disposal Gain'),
        (ACCOUNT_ASSET_DISPOSAL_LOSS, 'Asset Disposal Loss'),
        (ACCOUNT_PAYABLE_SALARIES, 'Salaries Payable'),
        (ACCOUNT_ACCRUED_LIABILITY, 'Accrued Liability'),
        (ACCOUNT_SECTOR_PAYABLE, 'حساب القطاع الإنتاجي'),
        (ACCOUNT_ZAKAT_EXPENSE, 'Zakat Expense'),
        (ACCOUNT_ZAKAT_PAYABLE, 'Zakat Payable'),
        (ACCOUNT_VAT_PAYABLE, 'ضريبة القيمة المضافة (VAT)'),
        (ACCOUNT_SUSPENSE, 'Suspense - Requires Review'),
    ]
    account_code = models.CharField(max_length=50, choices=ACCOUNT_CHOICES, db_index=True)
    
    debit = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    credit = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    
    description = models.CharField(max_length=255)
    
    currency = models.CharField(max_length=10, default="YER", help_text="Transaction Currency")
    tax_amount = models.DecimalField(max_digits=14, decimal_places=3, default=0, help_text="VAT/Tax Amount included")
    
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='ledger_created_new', editable=False, null=True)
    
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        related_name='ledger_approved_new',
        null=True, 
        blank=True
    )

    row_hash = models.CharField(max_length=64, editable=False)

    # [AGRI-GUARDIAN §1.II] Currency Snapshot: Store exchange rate at moment of transaction.
    # Historical reports MUST use this stored rate, NEVER the current system rate.
    exchange_rate_at_moment = models.DecimalField(
        max_digits=10, decimal_places=4, default=1,
        help_text="سعر الصرف لحظة تسجيل القيد المالي"
    )

    idempotency_key = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        help_text="لمنع تكرار القيد عند ضعف الإشارة V2",
    )

    # [AGRI-GUARDIAN] Posted entries are immutable evidence.
    # Field exists to support reporting filters and release-gate probes.
    is_posted = models.BooleanField(
        default=True, editable=False, db_index=True, help_text="Posted (locked) ledger entry"
    )
    objects = ScopedManager()

    class Meta:
        managed = True
        db_table = 'core_financialledger' # Safe-Move
        verbose_name = "قيد مالي"
        verbose_name_plural = "القيود المالية"
        constraints = [
            models.CheckConstraint(
                check=models.Q(debit__gte=0),
                name='financialledger_debit_non_negative_new'
            ),
            models.CheckConstraint(
                check=models.Q(credit__gte=0),
                name='financialledger_credit_non_negative_new'
            ),
            models.CheckConstraint(
                check=(
                    (models.Q(debit__gt=0) & models.Q(credit=0))
                    | (models.Q(credit__gt=0) & models.Q(debit=0))
                ),
                name='financialledger_debit_credit_xor_new'
            ),
        ]
        ordering = ['-created_at']

    def clean(self):
        super().clean()
        # [AGRI-GUARDIAN] STRICT FISCAL LOCKING
        # Validate that the transaction date is within an open fiscal period.
        # Uses lazy import to avoid circular dependency with FinanceService.
        from smart_agri.finance.services.core_finance import FinanceService
        
        # Determine the date to check. Ideally 'date' field, but Ledger uses 'created_at' (auto_now_add).
        # Since 'created_at' isn't populated until save, we rely on the intended date or today.
        # If this is an update (forbidden), we block it.
        if not self._state.adding:
             raise ValidationError("سجل غير قابل للتغيير: لا يمكن تحديث السجلات الموجودة.")

        if (self.debit > 0 and self.credit > 0) or (self.debit == 0 and self.credit == 0):
            raise ValidationError("Exactly one of debit/credit must be positive for each ledger row.")
        
        # Resolve farm scope for fiscal locking.
        # Treasury postings and other non-Activity sources MUST still respect fiscal close.
        farm = None
        if self.farm_id:
            farm = self.farm
        elif self.activity and self.activity.crop_plan:
            farm = self.activity.crop_plan.farm
        elif self.crop_plan and getattr(self.crop_plan, 'farm_id', None):
            farm = self.crop_plan.farm

        check_date = timezone.now().date()
        if farm is not None:
            latest_period = (
                FiscalPeriod.objects.filter(
                    fiscal_year__farm=farm,
                    deleted_at__isnull=True,
                )
                .order_by("-end_date", "-month", "-pk")
                .first()
            )
            if latest_period is not None:
                if check_date < latest_period.start_date:
                    check_date = latest_period.start_date
                elif check_date > latest_period.end_date:
                    check_date = latest_period.end_date

        if farm is not None:
            FinanceService.check_fiscal_period(check_date, farm, strict=True)

    @property
    def amount(self):
        return self.debit if self.debit > 0 else self.credit

    @amount.setter
    def amount(self, value):
        transaction_type = getattr(self, "transaction_type", "DEBIT")
        if transaction_type == "CREDIT":
            self.debit = Decimal("0")
            self.credit = value
        else:
            self.debit = value
            self.credit = Decimal("0")

    @property
    def transaction_type(self):
        return "CREDIT" if self.credit > 0 else "DEBIT"

    @transaction_type.setter
    def transaction_type(self, value):
        if value == "CREDIT" and self.debit > 0:
            self.credit = self.debit
            self.debit = Decimal("0")
        elif value != "CREDIT" and self.credit > 0:
            self.debit = self.credit
            self.credit = Decimal("0")


    def save(self, *args, **kwargs):
        is_create = self._state.adding

        # [AGRI-GUARDIAN] LEDGER IMMUTABILITY (Hard Stop)
        # Never UPDATE an existing ledger row. Corrections MUST be posted as new
        # reversal entries in an open period. This is critical for forensic chain-of-custody.
        if not is_create:
            raise ValidationError(
                "سجل القيود المالية (FinancialLedger) غير قابل للتعديل. "
                "أي تصحيح يجب أن يتم عبر قيد عكسي (Reversal) داخل فترة مفتوحة."
            )
        self.full_clean() # Enforce clean() before save
        
        # [AGRI-GUARDIAN] Auto-populate Farm
        if not self.farm_id and self.activity:
            if self.activity.crop_plan:
                self.farm = self.activity.crop_plan.farm
            elif self.activity.log:
                self.farm = self.activity.log.farm
            # Future: Logic for other transaction sources (Sales, etc.)
        
        source_ref = (
            f"{self.content_type_id}:{self.object_id}"
            if self.content_type_id and self.object_id
            else f"ACT:{self.activity_id}"
        )
        data_string = (
            f"{source_ref}|{self.account_code}|{self.debit}|{self.credit}|"
            f"{self.description}|{self.farm_id}|{self.id}|{self.exchange_rate_at_moment}"
        )
        self.row_hash = hashlib.sha256(data_string.encode('utf-8')).hexdigest()
        super().save(*args, **kwargs)

        if is_create:
            from smart_agri.core.services.sensitive_audit import log_sensitive_mutation

            log_sensitive_mutation(
                actor=self.created_by,
                action="create_sensitive",
                model_name="FinancialLedger",
                object_id=self.pk,
                reason=self.description or "ledger_posting",
                old_value=None,
                new_value={
                    "farm_id": self.farm_id,
                    "activity_id": self.activity_id,
                    "account_code": self.account_code,
                    "debit": str(self.debit),
                    "credit": str(self.credit),
                    "currency": self.currency,
                },
                farm_id=self.farm_id,
                context={"source": "financial_ledger_save"},
            )

    def delete(self, *args, **kwargs):
        # [AGRI-GUARDIAN] LEDGER IMMUTABILITY (Hard Stop)
        # Ledger rows are append-only. Use reversal entries instead of delete.
        raise ValidationError(
            "سجل القيود المالية (FinancialLedger) غير قابل للحذف. "
            "أي تصحيح يجب أن يتم عبر قيد عكسي (Reversal) داخل فترة مفتوحة."
        )

class ActualExpense(SoftDeleteModel):
    farm = models.ForeignKey("core.Farm", on_delete=models.CASCADE, related_name="actual_expenses_new")
    budget_classification = models.ForeignKey(
        BudgetClassification,
        on_delete=models.PROTECT,
        related_name="actual_expenses",
        null=True,
        blank=True,
        help_text="Approved BudgetCode for this expense.",
    )
    replenishment_reference = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Approved replenishment request reference.",
    )
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    date = models.DateField(default=timezone.now, verbose_name="التاريخ")
    amount = models.DecimalField(
        max_digits=19, 
        decimal_places=4, 
        verbose_name="المبلغ",
        help_text="المبلغ المالي بدقة عالية. يمنع استخدام Float."
    )
    description = models.CharField(max_length=255, verbose_name="الوصف")
    account_code = models.CharField(max_length=50, default=FinancialLedger.ACCOUNT_OVERHEAD, db_index=True)
    
    currency = models.CharField(max_length=10, default="YER", verbose_name="العملة")
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=4, default=Decimal("1.0000"), verbose_name="سعر الصرف")
    amount_local = models.DecimalField(max_digits=19, decimal_places=4, default=0, editable=False, verbose_name="المبلغ بالعملة المحلية")

    is_allocated = models.BooleanField(default=False, verbose_name="تم التخصيص؟")
    allocated_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default="open", db_index=True)

    # [AGRI-GUARDIAN] Forensic & Offline Columns (Syncs with SQL Patch)
    idempotency_key = models.UUIDField(null=True, blank=True, unique=True, help_text="Prevents double-spending")
    device_created_at = models.DateTimeField(null=True, blank=True, help_text="When it happened physically")
    local_device_id = models.CharField(max_length=64, null=True, blank=True, help_text="Device Fingerprint")

    # [AGRI-GUARDIAN §Axis-4] Fund Accounting: Revenue accounts are CUSTODIAL.
    # Expenses cannot be posted directly against revenue or receivable accounts.
    FORBIDDEN_EXPENSE_ACCOUNTS = frozenset([
        FinancialLedger.ACCOUNT_SALES_REVENUE,   # 5000-REVENUE
        FinancialLedger.ACCOUNT_RECEIVABLE,       # 1200-RECEIVABLE
        FinancialLedger.ACCOUNT_SECTOR_PAYABLE,   # 2100-SECTOR-PAY
    ])

    class Meta:
        db_table = 'core_actual_expense' # Safe-Move
        verbose_name = "مصروف فعلي"
        ordering = ['-date']
        unique_together = ('farm', 'description', 'period_start', 'period_end')
        permissions = (
            ("can_manage_expenses", "Can create/update/allocate actual expenses"),
        )

    def clean(self):
        super().clean()
        # [AGRI-GUARDIAN §Axis-4] FUND ACCOUNTING GUARD
        # Revenue is custodial — expenses MUST NOT debit revenue accounts.
        if self.account_code in self.FORBIDDEN_EXPENSE_ACCOUNTS:
            raise ValidationError({
                'account_code': (
                    f"SECURITY [Axis-4]: لا يجوز ترحيل مصروف على حساب إيرادات/ذمم "
                    f"({self.account_code}). إيرادات المزرعة أمانة تُحوَّل للقطاع."
                )
            })

class FiscalYear(SoftDeleteModel):
    """
    Defines a Fiscal Year for a Farm.
    """
    farm = models.ForeignKey("core.Farm", on_delete=models.CASCADE, related_name="fiscal_years")
    year = models.PositiveIntegerField(help_text="e.g. 2026")
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('farm', 'year')
        ordering = ['-year']
        verbose_name = "سنة مالية"
        verbose_name_plural = "السنوات المالية"

class FiscalPeriod(SoftDeleteModel):
    """
    Defines a monthly period within a Fiscal Year.
    Controls locking of transactions.
    """
    STATUS_OPEN = "open"
    STATUS_SOFT_CLOSE = "soft_close"
    STATUS_HARD_CLOSE = "hard_close"
    LEGACY_STATUS_SOFT_CLOSED = "soft_closed"
    LEGACY_STATUS_HARD_CLOSED = "hard_closed"
    STATUS_CHOICES = (
        (STATUS_OPEN, "Open"),
        (STATUS_SOFT_CLOSE, "Soft Close"),
        (STATUS_HARD_CLOSE, "Hard Close"),
        (LEGACY_STATUS_SOFT_CLOSED, "Soft Closed (Legacy)"),
        (LEGACY_STATUS_HARD_CLOSED, "Hard Closed (Legacy)"),
    )

    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.CASCADE, related_name="periods")
    month = models.PositiveIntegerField(help_text="1-12")
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN)
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ('fiscal_year', 'month')
        ordering = ['fiscal_year', 'month']
        verbose_name = "فترة مالية"
        verbose_name_plural = "الفترات المالية"
        permissions = (
            ("can_hard_close_period", "يمكنه إغلاق الفترات المالية نهائياً"),
            ("can_sector_finance_approve", "يمكنه تقديم اعتماد مالي نهائي للقطاع"),
        )

    def clean(self):
        super().clean()
        if self.pk:
            previous = FiscalPeriod.objects.get(pk=self.pk)
            previous_status = self._normalize_status(previous.status)
            current_status = self._normalize_status(self.status)

            # [AGRI-GUARDIAN §Axis-3] STRICT Fiscal State Machine.
            # Allowed transitions ONLY:
            #   open → soft_close → hard_close
            # Forbidden: any backward transition, open → hard_close skip

            if getattr(self, '_allow_reopen', False):
                pass
            elif previous_status == self.STATUS_HARD_CLOSE and current_status != self.STATUS_HARD_CLOSE:
                raise ValidationError(
                    "SECURITY [Axis-3]: لا يمكن إعادة فتح فترة مغلقة نهائياً (Hard Close). "
                    "أي تصحيح يجب أن يتم عبر قيد عكسي في فترة مفتوحة."
                )

            elif previous_status == self.STATUS_SOFT_CLOSE and current_status == self.STATUS_OPEN:
                raise ValidationError(
                    "SECURITY [Axis-3]: لا يمكن إعادة فتح فترة في مرحلة الإغلاق الأولي. "
                    "يجب المضي للإغلاق النهائي أو إنشاء قيد عكسي في فترة مفتوحة."
                )

            if previous_status == self.STATUS_OPEN and current_status == self.STATUS_HARD_CLOSE:
                raise ValidationError(
                    "SECURITY [Axis-3]: لا يمكن الانتقال مباشرة من 'مفتوحة' إلى 'مغلقة نهائياً'. "
                    "يجب المرور بمرحلة الإغلاق الأولي (Soft Close) أولاً."
                )
    def __str__(self):
        return f"{self.fiscal_year.year}-{self.month} ({self.status.replace('_', ' ').title()})"

    @staticmethod
    def _normalize_status(status):
        if status == FiscalPeriod.LEGACY_STATUS_SOFT_CLOSED:
            return FiscalPeriod.STATUS_SOFT_CLOSE
        if status == FiscalPeriod.LEGACY_STATUS_HARD_CLOSED:
            return FiscalPeriod.STATUS_HARD_CLOSE
        return status

    def save(self, *args, **kwargs):
        self.status = self._normalize_status(self.status)
        if self.status == self.STATUS_OPEN:
            self.is_closed = False
        else:
            self.is_closed = True
        update_fields = kwargs.get('update_fields')
        if update_fields is not None:
            update_fields = set(update_fields)
            update_fields.add('is_closed')
            update_fields.add('status')
            kwargs['update_fields'] = list(update_fields)
        super().save(*args, **kwargs)

class WorkerAdvance(SoftDeleteModel):
    """
    [AGRI-GUARDIAN] Track daily cash advances (Salif/Masroof).
    These are liabilities on the worker, deducted from Payroll.
    Protocol XXIX: The Daily Cash Control.
    """
    # Corrected FK to 'core.Employee' instead of 'core.Worker' based on audit
    worker = models.ForeignKey('core.Employee', on_delete=models.PROTECT, related_name='advances')
    amount = models.DecimalField(max_digits=12, decimal_places=4, help_text="قيمة المسحوب/السلفة") # Strict Decimal
    date = models.DateField(auto_now_add=True)
    
    # Who authorized/gave the cash?
    supervisor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='advances_authorized')
    
    is_deducted = models.BooleanField(default=False, help_text="هل تم خصمها من الراتب النهائي؟")
    notes = models.TextField(blank=True, help_text="سبب السلفة (قات، غداء، علاج...)")
    
    # Link to PayrollSlip if deducted?
    deducted_in_slip = models.ForeignKey('core.PayrollSlip', null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        verbose_name = "مسحوب يومي"
        indexes = [models.Index(fields=['worker', 'is_deducted'])]

    def clean(self):
        # Validation: Check if supervisor holds enough cash custody
        if self.amount <= 0:
             raise ValidationError("Amount must be positive.")


class ApprovalRule(SoftDeleteModel):
    ROLE_MANAGER = "MANAGER"
    ROLE_FARM_FINANCE_MANAGER = "FARM_FINANCE_MANAGER"
    ROLE_SECTOR_ACCOUNTANT = "SECTOR_ACCOUNTANT"
    ROLE_SECTOR_REVIEWER = "SECTOR_REVIEWER"
    ROLE_CHIEF_ACCOUNTANT = "SECTOR_CHIEF_ACCOUNTANT"
    ROLE_FINANCE_DIRECTOR = "FINANCE_DIRECTOR"
    ROLE_SECTOR_DIRECTOR = "SECTOR_DIRECTOR"
    ROLE_CHOICES = [
        (ROLE_MANAGER, "Farm Manager"),
        (ROLE_FARM_FINANCE_MANAGER, "Farm Finance Manager"),
        (ROLE_SECTOR_ACCOUNTANT, "Sector Accountant"),
        (ROLE_SECTOR_REVIEWER, "Sector Reviewer"),
        (ROLE_CHIEF_ACCOUNTANT, "Sector Chief Accountant"),
        (ROLE_FINANCE_DIRECTOR, "Sector Finance Director"),
        (ROLE_SECTOR_DIRECTOR, "Sector Director"),
    ]

    MODULE_FINANCE = "FINANCE"
    MODULE_INVENTORY = "INVENTORY"
    MODULE_PROCUREMENT = "PROCUREMENT"
    MODULE_CHOICES = [
        (MODULE_FINANCE, "Finance"),
        (MODULE_INVENTORY, "Inventory"),
        (MODULE_PROCUREMENT, "Procurement"),
    ]

    farm = models.ForeignKey("core.Farm", on_delete=models.CASCADE, related_name="approval_rules")
    module = models.CharField(max_length=20, choices=MODULE_CHOICES, default=MODULE_FINANCE)
    action = models.CharField(max_length=60, default="expense_posting")
    
    # [ULTIMATE EDITION] Dynamic Routing Conditions
    cost_center = models.ForeignKey(
        'finance.CostCenter', on_delete=models.CASCADE, null=True, blank=True,
        related_name='approval_rules',
        help_text="تخصيص القاعدة لمركز تكلفة محدد (يترك فارغاً للكل)"
    )
    
    min_amount = models.DecimalField(max_digits=19, decimal_places=4, default=Decimal("0.0000"))
    max_amount = models.DecimalField(
        max_digits=19, decimal_places=4, null=True, blank=True,
        help_text="الحد الأقصى للمبلغ (يترك فارغاً إذا كان مفتوحاً لغاية السلطة المالية المحددة)"
    )
    
    required_role = models.CharField(max_length=30, choices=ROLE_CHOICES, default=ROLE_MANAGER)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "finance_approvalrule"
        verbose_name = "قاعدة اعتماد مالي"
        verbose_name_plural = "قواعد الاعتماد المالي"
        indexes = [
            models.Index(fields=["farm", "module", "action", "is_active"]),
        ]


class ApprovalRequest(SoftDeleteModel):
    STATUS_PENDING = "PENDING"
    STATUS_APPROVED = "APPROVED"
    STATUS_REJECTED = "REJECTED"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    ]

    farm = models.ForeignKey("core.Farm", on_delete=models.CASCADE, related_name="approval_requests")
    module = models.CharField(max_length=20, choices=ApprovalRule.MODULE_CHOICES, default=ApprovalRule.MODULE_FINANCE)
    action = models.CharField(max_length=60, default="expense_posting")

    # [ULTIMATE EDITION]
    cost_center = models.ForeignKey(
        'finance.CostCenter', on_delete=models.PROTECT, null=True, blank=True,
        related_name='approval_requests',
        help_text="السياق التحليلي للطلب (يستخدم كعامل توجيه للاعتماد)"
    )

    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT, null=True, blank=True)
    object_id = models.CharField(max_length=36, null=True, blank=True)
    transaction_source = GenericForeignKey("content_type", "object_id")
    requested_amount = models.DecimalField(max_digits=19, decimal_places=4, default=Decimal("0.0000"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    required_role = models.CharField(
        max_length=30,
        choices=ApprovalRule.ROLE_CHOICES,
        default=ApprovalRule.ROLE_MANAGER,
        help_text="الدور المطلوب في المرحلة الحالية من سلسلة الاعتماد.",
    )
    final_required_role = models.CharField(
        max_length=30,
        choices=ApprovalRule.ROLE_CHOICES,
        default=ApprovalRule.ROLE_MANAGER,
        help_text="الدور النهائي المطلوب لاعتماد الطلب بالكامل.",
    )
    current_stage = models.PositiveSmallIntegerField(default=1)
    total_stages = models.PositiveSmallIntegerField(default=1)
    approval_history = models.JSONField(default=list, blank=True)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="approval_requests_created")
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="approval_requests_approved"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        db_table = "finance_approvalrequest"
        verbose_name = "طلب اعتماد مالي"
        verbose_name_plural = "طلبات الاعتماد المالي"
        indexes = [
            models.Index(fields=["farm", "status", "module", "action"]),
            models.Index(fields=["farm", "status", "required_role"]),
        ]
        permissions = (
            ("can_approve_finance_request", "يمكنه الموافقة على طلبات الاعتماد المالي"),
        )

class ApprovalStageEvent(models.Model):
    ACTION_CREATED = "CREATED"
    ACTION_STAGE_APPROVED = "STAGE_APPROVED"
    ACTION_FINAL_APPROVED = "FINAL_APPROVED"
    ACTION_REJECTED = "REJECTED"
    ACTION_REOPENED = "REOPENED"
    ACTION_OVERRIDDEN = "OVERRIDDEN"
    ACTION_AUTO_ESCALATED = "AUTO_ESCALATED"
    ACTION_CHOICES = [
        (ACTION_CREATED, "Created"),
        (ACTION_STAGE_APPROVED, "Stage Approved"),
        (ACTION_FINAL_APPROVED, "Final Approved"),
        (ACTION_REJECTED, "Rejected"),
        (ACTION_REOPENED, "Reopened"),
        (ACTION_OVERRIDDEN, "Overridden"),
        (ACTION_AUTO_ESCALATED, "Auto Escalated"),
    ]

    request = models.ForeignKey(
        'finance.ApprovalRequest',
        on_delete=models.CASCADE,
        related_name='stage_events',
    )
    stage_number = models.PositiveSmallIntegerField(default=1)
    role = models.CharField(max_length=30, choices=ApprovalRule.ROLE_CHOICES)
    action_type = models.CharField(max_length=24, choices=ACTION_CHOICES)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='approval_stage_events',
    )
    note = models.CharField(max_length=500, blank=True, default='')
    snapshot = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'finance_approvalstageevent'
        verbose_name = 'حدث مرحلة اعتماد'
        verbose_name_plural = 'أحداث مراحل الاعتماد'
        ordering = ['request_id', 'stage_number', 'created_at', 'id']
        indexes = [
            models.Index(fields=['request', 'stage_number']),
            models.Index(fields=['action_type', 'created_at']),
        ]

class FinanceAuditLog(models.Model):
    """
    [AGRI-GUARDIAN] Read-Only view of the Shadow Ledger.
    Mapped to SQL Table: finance_audit_log_finance
    Propagated by DB Triggers, not Django.
    """
    expense_id = models.IntegerField()
    old_amount = models.DecimalField(max_digits=19, decimal_places=4, null=True)
    new_amount = models.DecimalField(max_digits=19, decimal_places=4, null=True)
    changed_by_user = models.CharField(max_length=100)
    change_type = models.CharField(max_length=10)
    changed_at = models.DateTimeField()
    client_ip = models.CharField(max_length=45, null=True)
    notes = models.TextField(null=True)

    class Meta:
        managed = False # Created by SQL Patch
        db_table = 'finance_audit_log_finance'
        verbose_name = "سجل التدقيق الجنائي"
        ordering = ['-changed_at']

# Treasury module models live in models_treasury.py to reduce coupling.
from .models_treasury import CashBox, TreasuryTransaction  # noqa: E402,F401
from .models_petty_cash import PettyCashRequest, PettyCashSettlement, PettyCashLine  # noqa: E402,F401
from .models_supplier_settlement import SupplierSettlement, SupplierSettlementPayment  # noqa: E402,F401
