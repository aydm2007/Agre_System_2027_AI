# pyright: reportArgumentType=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportOperatorIssue=false
# pyright: reportAttributeAccessIssue=false
from django.db import models
from django.db.models import Sum
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from .base import SoftDeleteModel
from .farm import Farm

class EmploymentCategory(models.TextChoices):
    OFFICIAL = 'OFFICIAL', 'موظف رسمي (راتب مركزي)'
    CASUAL = 'CASUAL', 'أجر يومي (تمويل ذاتي)'


class EmployeeRole(models.TextChoices):
    """[Axis 1] Schema Parity — أنواع الموظفين."""
    WORKER = 'Worker', 'عامل مزرعة'
    ENGINEER = 'Engineer', 'مهندس زراعي'
    MANAGER = 'Manager', 'مدير مزرعة'
    ADMIN = 'Admin', 'إداري'


class Employee(SoftDeleteModel):
    """
    Registry of all staff members (Workers, Engineers, Managers).
    Integrates with Auth User if they have login access.
    """
    # [Axis 1] Backward-compatible constants
    TYPE_WORKER = EmployeeRole.WORKER
    TYPE_ENGINEER = EmployeeRole.ENGINEER
    TYPE_MANAGER = EmployeeRole.MANAGER
    TYPE_ADMIN = EmployeeRole.ADMIN
    PAYMENT_MODES = [
        ('OFFICIAL', 'Official Salary (Central)'),
        ('SURRA', 'Shift Rate (Surra)'),
        ('PIECE', 'Piece Rate (Muqawala)'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, blank=True, 
        related_name="employee_profile",
        verbose_name="المستخدم المرتبط"
    )
    farm = models.ForeignKey(Farm, on_delete=models.PROTECT, related_name="employees", verbose_name="المزرعة")
    
    first_name = models.CharField(max_length=100, verbose_name="الاسم الأول")
    last_name = models.CharField(max_length=100, verbose_name="اسم العائلة")
    employee_id = models.CharField(max_length=50, unique=True, help_text="الرقم التعريفي الداخلي / رقم الشارة", verbose_name="الرقم الوظيفي")
    
    id_number = models.CharField(max_length=50, blank=True, default="", help_text="الهوية الوطنية / الإقامة", verbose_name="رقم الهوية")
    role = models.CharField(max_length=20, choices=EmployeeRole.choices, default=EmployeeRole.WORKER, verbose_name="الدور الوظيفي")
    category = models.CharField(
        max_length=20,
        choices=EmploymentCategory.choices,
        default=EmploymentCategory.CASUAL,
        verbose_name="فئة التوظيف"
    )
    payment_mode = models.CharField(
        max_length=10,
        choices=PAYMENT_MODES,
        default='SURRA',
        verbose_name="طريقة الدفع"
    )

    base_salary = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text="للموظفين الرسميين فقط",
        verbose_name="الراتب الأساسي"
    )
    shift_rate = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text="قيمة الصرة اليومية للعمالة بالأجر اليومي",
        verbose_name="أجر الوردية (الصرة)"
    )
    hourly_rate = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text="أجر الساعة للفرد (يُستخدم في نظام الساعة أو الإنتاج العالي)",
        verbose_name="أجر الساعة"
    )
    guarantor_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="مطلوب للعمال المؤقتين (الضامن/المشرف)",
        verbose_name="اسم الضامن"
    )
    
    # [AGRI-GUARDIAN] Smart Card / QR identification fields
    card_id = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        default=None,
        unique=True,
        db_index=True,
        help_text="معرّف البطاقة الذكية (NFC/RFID) — يُستخدم لتسجيل الحضور التلقائي",
        verbose_name="رقم البطاقة الذكية"
    )
    qr_code = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        default=None,
        unique=True,
        db_index=True,
        help_text="رمز QR فريد للعامل — يُمسح ميدانياً لربط العامل بالنشاط تلقائياً",
        verbose_name="رمز QR"
    )
    
    joined_date = models.DateField(default=timezone.localdate, verbose_name="تاريخ الالتحاق")
    is_active = models.BooleanField(default=True, verbose_name="نشط")

    class Meta:
        verbose_name = "موظف"
        verbose_name_plural = "الموظفون"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.employee_id})"

    def clean(self):
        super().clean()
        base_salary = self.base_salary or Decimal("0.0000")
        shift_rate = self.shift_rate or Decimal("0.0000")

        if self.category == EmploymentCategory.OFFICIAL:
            if shift_rate > 0:
                raise ValidationError(
                    "الموظف الرسمي (مركزي) لا يمكن أن يتقاضى أجراً يومياً (صرة). يجب تصفير 'shift_rate'."
                )
            if base_salary <= 0:
                raise ValidationError("الموظف الرسمي يجب أن يكون له راتب أساسي محدد.")

        if self.category == EmploymentCategory.CASUAL:
            if base_salary > 0:
                raise ValidationError(
                    "العامل بالأجر اليومي (تمويل ذاتي) لا يمكن أن يكون له راتب أساسي. استخدم 'shift_rate'."
                )
            if self.payment_mode == 'SURRA' and shift_rate <= 0:
                raise ValidationError("عامل الصرة يجب أن يكون له قيمة وردية محددة.")

    def calculate_crop_cost(self, shifts, rate):
        return self.calculate_daily_cost(units_completed=shifts or 1, rate_override=rate)

    def calculate_daily_cost(self, units_completed=1, rate_override=None):
        if self.payment_mode == 'OFFICIAL' or self.category == EmploymentCategory.OFFICIAL:
            return Decimal('0.0000')
        if self.payment_mode == 'SURRA':
            return self.shift_rate
        if self.payment_mode == 'PIECE':
            unit_rate = rate_override if rate_override is not None else self.shift_rate
            return Decimal(str(unit_rate)) * Decimal(str(units_completed))
        return Decimal('0.0000')

class EmploymentContract(SoftDeleteModel):
    """
    Financial terms of employment. Used for Payroll Calculation.
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="contracts")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    
    basic_salary = models.DecimalField(max_digits=19, decimal_places=4, help_text="Monthly Basic")
    housing_allowance = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    transport_allowance = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    other_allowance = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    
    overtime_shift_value = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        default=0,
        help_text="قيمة الوردية الإضافية (قيمة الصرة الإضافية) - ريال يمني",
    )
    
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "عقد عمل"
        verbose_name_plural = "عقود العمل"

    def total_monthly_package(self):
        return self.basic_salary + self.housing_allowance + self.transport_allowance + self.other_allowance

    def __str__(self):
        return f"Contract: {self.employee} ({self.start_date})"

class Timesheet(SoftDeleteModel):
    """
    سجل الدوام اليومي (نظام الصرة - Surrah System).
    شمال اليمن: لا يوجد حساب بالساعة. التعامل بالوردية (1.0 يوم كامل، 0.5 نصف يوم).
    [AGENTS.md §139-144] الموظف الرسمي = حضور فقط، المؤقت = تكلفة محصول.
    [Axis 6] farm FK مباشر لعزل المستأجر.
    """
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="timesheets", verbose_name="الموظف")
    farm = models.ForeignKey(
        Farm, on_delete=models.PROTECT, related_name="timesheets",
        help_text="[Axis 6] عزل المزرعة — مطلوب لكل صف معاملات", verbose_name="المزرعة"
    )
    date = models.DateField(db_index=True, verbose_name="التاريخ")

    # Optional link to a specific Activity if tracking granular cost
    activity = models.ForeignKey(
        "core.Activity",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="timesheet_entries", verbose_name="النشاط الزراعي"
    )

    # نظام الصرة (الوردية) — Axis 5: Surra is the financial labor unit
    surrah_count = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("1.00"),
        help_text="عدد الصرات: 1.0 = يوم كامل، 0.5 = نصف يوم", verbose_name="عدد الصرات (الورديات)"
    )
    surrah_overtime = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="إضافي بنظام الصرة (مثلاً 0.25 لربع يوم إضافي)", verbose_name="إضافي الصرة"
    )

    is_approved = models.BooleanField(default=False, verbose_name="تم الاعتماد")
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="approved_timesheets", verbose_name="اعتمد بواسطة"
    )

    class Meta:
        verbose_name = "سجل دوام"
        verbose_name_plural = "سجلات الدوام"
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['farm', 'date']),
        ]

    def clean(self):
        super().clean()
        if self.employee_id and self.farm_id:
            if self.employee.farm_id != self.farm_id:
                raise ValidationError(
                    "[Axis 6] الموظف لا ينتمي لهذه المزرعة."
                )

    def __str__(self):
        return f"{self.employee} — {self.date} ({self.surrah_count} صرة)"

class PayrollStatus(models.TextChoices):
    """[Axis 1] Schema Parity — حالات محددة بدل نص حر."""
    DRAFT = 'DRAFT', 'مسودة'
    APPROVED = 'APPROVED', 'معتمد'
    PAID = 'PAID', 'مدفوع'
    CANCELLED = 'CANCELLED', 'ملغي'


class PayrollRun(SoftDeleteModel):
    """
    مسير الرواتب الشهري.
    [AGENTS.md Phase 4] Employee.category segregation.
    [Axis 7] approved_by audit trail.
    """
    farm = models.ForeignKey(Farm, on_delete=models.PROTECT, related_name="payroll_runs")
    period_start = models.DateField()
    period_end = models.DateField()

    total_amount = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    status = models.CharField(
        max_length=20,
        choices=PayrollStatus.choices,
        default=PayrollStatus.DRAFT,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="created_payroll_runs",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="approved_payroll_runs",
        help_text="[Axis 7] Audit trail — من اعتمد المسير",
    )

    class Meta:
        verbose_name = "مسير رواتب"
        verbose_name_plural = "مسيرات الرواتب"

    def recalculate_total(self):
        """حساب إجمالي المسير من القسائم — Decimal safe (Axis 5)."""
        self.total_amount = self.slips.aggregate(
            total=Sum('net_pay')
        )['total'] or Decimal('0.0000')

    def __str__(self):
        return f"مسير {self.farm} — {self.period_start} → {self.period_end} ({self.get_status_display()})"

class PayrollSlip(SoftDeleteModel):
    """
    Individual Payslip for an employee within a run.
    """
    run = models.ForeignKey(PayrollRun, on_delete=models.CASCADE, related_name="slips")
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT)
    
    basic_amount = models.DecimalField(max_digits=19, decimal_places=4)
    allowances_amount = models.DecimalField(max_digits=19, decimal_places=4)
    overtime_amount = models.DecimalField(max_digits=19, decimal_places=4)
    deductions_amount = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    net_pay = models.DecimalField(max_digits=19, decimal_places=4)
    
    days_worked = models.DecimalField(max_digits=5, decimal_places=1)

    class Meta:
        verbose_name = "قسيمة راتب"
        verbose_name_plural = "قسائم الرواتب"


class AdvanceStatus(models.TextChoices):
    """[Axis 1] Schema Parity — حالات السلفيات."""
    PENDING = 'PENDING', 'قيد الانتظار'
    APPROVED = 'APPROVED', 'معتمدة'
    DEDUCTED = 'DEDUCTED', 'مخصومة'
    CANCELLED = 'CANCELLED', 'ملغاة'


class EmployeeAdvance(SoftDeleteModel):
    """
    سلفيات العمال — Employee Advances.
    [AGENTS.md Phase 3] Financial integrity for worker loans.
    [Axis 2] idempotency_key prevents duplicate submissions.
    [Axis 5] Decimal(19,4) for amount — no floats.
    [Axis 6] farm_id mandatory — tenant isolation.
    [Axis 7] approved_by audit trail.
    """
    employee = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name="hr_advances", verbose_name="الموظف/العامل"
    )
    farm = models.ForeignKey(
        Farm, on_delete=models.PROTECT, related_name="employee_advances",
        help_text="[Axis 6] عزل المزرعة — مطلوب لكل صف معاملات", verbose_name="المزرعة"
    )
    amount = models.DecimalField(
        max_digits=19, decimal_places=4,
        help_text="[Axis 5] Decimal-safe المبلغ", verbose_name="المبلغ"
    )
    date = models.DateField(verbose_name="تاريخ السلفية")
    reason = models.CharField(max_length=200, blank=True, default='', verbose_name="سبب السلفية")
    status = models.CharField(
        max_length=20,
        choices=AdvanceStatus.choices,
        default=AdvanceStatus.PENDING,
        verbose_name="الحالة"
    )
    idempotency_key = models.UUIDField(
        unique=True, null=True, blank=True,
        help_text="[Axis 2] مفتاح عدم التكرار", verbose_name="مفتاح الحماية"
    )

    # Payroll integration
    deducted_in_slip = models.ForeignKey(
        PayrollSlip, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="deducted_advances",
        help_text="القسيمة التي خُصم منها المبلغ", verbose_name="خُصمت في قسيمة الدفع"
    )

    # Audit trail
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="created_advances", verbose_name="تم الإنشاء بواسطة"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="approved_advances",
        help_text="[Axis 7] Audit trail — من اعتمد السلفية", verbose_name="مُعتمد السلفية"
    )

    class Meta:
        verbose_name = "سلفية موظف"
        verbose_name_plural = "سلفيات الموظفين"
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['farm', 'status']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['idempotency_key'],
                condition=models.Q(idempotency_key__isnull=False),
                name='unique_advance_idempotency_key',
            ),
        ]

    def clean(self):
        super().clean()
        if self.employee_id and self.farm_id:
            if self.employee.farm_id != self.farm_id:
                raise ValidationError(
                    "[Axis 6] الموظف لا ينتمي لهذه المزرعة."
                )

    def __str__(self):
        return f"سلفية {self.employee} — {self.amount} ({self.get_status_display()})"

