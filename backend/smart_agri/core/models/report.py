from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal


class AsyncReportRequest(models.Model):
    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_RUNNING, "Running"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
    ]

    REPORT_PROFITABILITY = "profitability"
    REPORT_ADVANCED = "advanced"
    REPORT_COMMERCIAL_PDF = "commercial_pdf"
    REPORT_TYPES = [
        (REPORT_PROFITABILITY, "Profitability"),
        (REPORT_ADVANCED, "Advanced Overview"),
        (REPORT_COMMERCIAL_PDF, "Commercial PDF"),
    ]
    EXPORT_TYPE_ADVANCED_REPORT = "advanced_report"
    EXPORT_TYPE_INVENTORY_BALANCE = "inventory_balance"
    EXPORT_TYPE_INVENTORY_MOVEMENTS = "inventory_movements"
    EXPORT_TYPE_INVENTORY_LOW_STOCK = "inventory_low_stock"
    EXPORT_TYPE_DAILY_EXECUTION_SUMMARY = "daily_execution_summary"
    EXPORT_TYPE_DAILY_EXECUTION_DETAIL = "daily_execution_detail"
    EXPORT_TYPE_PLAN_ACTUAL_VARIANCE = "plan_actual_variance"
    EXPORT_TYPE_PERENNIAL_TREE_BALANCE = "perennial_tree_balance"
    EXPORT_TYPE_OPERATIONAL_READINESS = "operational_readiness"
    EXPORT_TYPE_INVENTORY_EXPIRY_BATCHES = "inventory_expiry_batches"
    EXPORT_TYPE_FUEL_POSTURE_REPORT = "fuel_posture_report"
    EXPORT_TYPE_FIXED_ASSET_REGISTER = "fixed_asset_register"
    EXPORT_TYPE_CONTRACT_OPERATIONS_POSTURE = "contract_operations_posture"
    EXPORT_TYPE_SUPPLIER_SETTLEMENT_POSTURE = "supplier_settlement_posture"
    EXPORT_TYPE_PETTY_CASH_POSTURE = "petty_cash_posture"
    EXPORT_TYPE_RECEIPTS_DEPOSIT_POSTURE = "receipts_deposit_posture"
    EXPORT_TYPE_GOVERNANCE_WORK_QUEUE = "governance_work_queue"
    EXPORT_TYPE_CHOICES = [
        (EXPORT_TYPE_ADVANCED_REPORT, "Advanced Report"),
        (EXPORT_TYPE_INVENTORY_BALANCE, "Inventory Balance"),
        (EXPORT_TYPE_INVENTORY_MOVEMENTS, "Inventory Movements"),
        (EXPORT_TYPE_INVENTORY_LOW_STOCK, "Inventory Low Stock"),
    ]

    FORMAT_JSON = "json"
    FORMAT_XLSX = "xlsx"
    FORMAT_PDF = "pdf"
    FORMAT_CHOICES = [
        (FORMAT_JSON, "JSON"),
        (FORMAT_XLSX, "XLSX"),
        (FORMAT_PDF, "PDF"),
    ]

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="async_reports",
    )
    report_type = models.CharField(max_length=60, choices=REPORT_TYPES)
    params = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    export_type = models.CharField(
        max_length=60,
        choices=EXPORT_TYPE_CHOICES,
        default=EXPORT_TYPE_ADVANCED_REPORT,
    )
    output_format = models.CharField(max_length=16, choices=FORMAT_CHOICES, default=FORMAT_JSON)
    template_code = models.CharField(max_length=80, blank=True, default="")
    template_version = models.CharField(max_length=32, blank=True, default="v1")
    locale = models.CharField(max_length=16, blank=True, default="ar-YE")
    rtl = models.BooleanField(default=True)
    output_filename = models.CharField(max_length=255, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    requested_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    result_url = models.CharField(max_length=512, blank=True, default="")
    error_message = models.TextField(blank=True, default="")

    class Meta:
        db_table = "core_async_report"
        indexes = [
            models.Index(fields=["report_type"]),
            models.Index(fields=["status"]),
        ]

    def mark_running(self):
        self.status = self.STATUS_RUNNING
        self.save(update_fields=["status"])

    def mark_completed(self, url: str):
        self.status = self.STATUS_COMPLETED
        self.result_url = url
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "result_url", "completed_at"])

    def mark_failed(self, error: str):
        self.status = self.STATUS_FAILED
        self.error_message = error[:1024]
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "error_message", "completed_at"])

    @property
    def effective_export_type(self) -> str:
        if self.export_type:
            return self.export_type
        if self.report_type == self.REPORT_COMMERCIAL_PDF:
            return self.EXPORT_TYPE_ADVANCED_REPORT
        return self.EXPORT_TYPE_ADVANCED_REPORT


class AsyncImportJob(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_UPLOADED = "uploaded"
    STATUS_VALIDATED = "validated"
    STATUS_PREVIEW_READY = "preview_ready"
    STATUS_APPROVED_FOR_APPLY = "approved_for_apply"
    STATUS_APPLIED = "applied"
    STATUS_PARTIALLY_REJECTED = "partially_rejected"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_UPLOADED, "Uploaded"),
        (STATUS_VALIDATED, "Validated"),
        (STATUS_PREVIEW_READY, "Preview Ready"),
        (STATUS_APPROVED_FOR_APPLY, "Approved For Apply"),
        (STATUS_APPLIED, "Applied"),
        (STATUS_PARTIALLY_REJECTED, "Partially Rejected"),
        (STATUS_FAILED, "Failed"),
    ]

    MODULE_INVENTORY = "inventory"
    MODULE_PLANNING = "planning"
    MODULE_CHOICES = [
        (MODULE_INVENTORY, "Inventory"),
        (MODULE_PLANNING, "Planning"),
    ]

    TEMPLATE_INVENTORY_COUNT_SHEET = "inventory_count_sheet"
    TEMPLATE_INVENTORY_OPERATIONAL_ADJUSTMENT = "inventory_operational_adjustment"
    TEMPLATE_INVENTORY_OPENING_BALANCE = "inventory_opening_balance"
    TEMPLATE_INVENTORY_ITEM_MASTER = "inventory_item_master"
    TEMPLATE_PLANNING_MASTER_SCHEDULE = "planning_master_schedule"
    TEMPLATE_PLANNING_CROP_PLAN_STRUCTURE = "planning_crop_plan_structure"
    TEMPLATE_PLANNING_CROP_PLAN_BUDGET = "planning_crop_plan_budget"
    TEMPLATE_CHOICES = [
        (TEMPLATE_INVENTORY_COUNT_SHEET, "Inventory Count Sheet"),
        (TEMPLATE_INVENTORY_OPERATIONAL_ADJUSTMENT, "Inventory Operational Adjustment"),
        (TEMPLATE_INVENTORY_OPENING_BALANCE, "Inventory Opening Balance"),
        (TEMPLATE_INVENTORY_ITEM_MASTER, "Inventory Item Master"),
        (TEMPLATE_PLANNING_MASTER_SCHEDULE, "Planning Master Schedule"),
        (TEMPLATE_PLANNING_CROP_PLAN_STRUCTURE, "Planning Crop Plan Structure"),
        (TEMPLATE_PLANNING_CROP_PLAN_BUDGET, "Planning Crop Plan Budget"),
    ]

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="async_import_jobs",
    )
    farm = models.ForeignKey(
        "core.Farm",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="async_import_jobs",
    )
    module = models.CharField(max_length=40, choices=MODULE_CHOICES, default=MODULE_INVENTORY)
    template_code = models.CharField(max_length=80, choices=TEMPLATE_CHOICES)
    template_version = models.CharField(max_length=32, blank=True, default="v1")
    mode_context = models.CharField(max_length=16, blank=True, default="")
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    requested_at = models.DateTimeField(default=timezone.now)
    validated_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    uploaded_file = models.FileField(upload_to="imports/uploads/%Y/%m/%d/", null=True, blank=True)
    uploaded_filename = models.CharField(max_length=255, blank=True, default="")
    error_workbook = models.FileField(upload_to="imports/errors/%Y/%m/%d/", null=True, blank=True)
    preview_rows = models.JSONField(default=list, blank=True)
    validation_summary = models.JSONField(default=dict, blank=True)
    result_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    row_count = models.PositiveIntegerField(default=0)
    applied_count = models.PositiveIntegerField(default=0)
    rejected_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True, default="")

    class Meta:
        db_table = "core_async_import_job"
        indexes = [
            models.Index(fields=["module", "template_code"]),
            models.Index(fields=["status"]),
            models.Index(fields=["farm"]),
        ]

    def mark_uploaded(self, *, uploaded_filename: str):
        self.status = self.STATUS_UPLOADED
        self.uploaded_filename = uploaded_filename[:255]
        self.save(update_fields=["status", "uploaded_filename"])

    def mark_preview_ready(self, *, preview_rows, validation_summary, row_count, rejected_count):
        self.status = self.STATUS_PREVIEW_READY
        self.preview_rows = preview_rows
        self.validation_summary = validation_summary
        self.row_count = row_count
        self.rejected_count = rejected_count
        self.validated_at = timezone.now()
        self.save(
            update_fields=[
                "status",
                "preview_rows",
                "validation_summary",
                "row_count",
                "rejected_count",
                "validated_at",
            ]
        )

    def mark_approved_for_apply(self):
        self.status = self.STATUS_APPROVED_FOR_APPLY
        self.approved_at = timezone.now()
        self.save(update_fields=["status", "approved_at"])

    def mark_applied(self, *, applied_count, rejected_count, result_summary):
        self.status = self.STATUS_APPLIED if rejected_count == 0 else self.STATUS_PARTIALLY_REJECTED
        self.applied_count = applied_count
        self.rejected_count = rejected_count
        self.result_summary = result_summary
        self.applied_at = timezone.now()
        self.save(
            update_fields=[
                "status",
                "applied_count",
                "rejected_count",
                "result_summary",
                "applied_at",
            ]
        )

    def mark_failed(self, error: str):
        self.status = self.STATUS_FAILED
        self.error_message = error[:1024]
        self.save(update_fields=["status", "error_message"])


class VarianceAlert(models.Model):
    """
    جدول احتساب الظل (Shadow Ledger).
    يخزن كافة التجاوزات المالية والفنية التي حدثت في الميدان ليتم
    التحقيق فيها لاحقاً من قبل الإدارة في صنعاء.

    يتم إنشاء السجلات بواسطة ShadowVarianceEngine في حالة Shadow Mode فقط.
    في حالة Strict ERP Mode يتم رفض العملية قبل الحفظ.
    """
    ALERT_STATUS_UNINVESTIGATED = 'UNINVESTIGATED'
    ALERT_STATUS_UNDER_REVIEW = 'UNDER_REVIEW'
    ALERT_STATUS_RESOLVED_JUSTIFIED = 'RESOLVED_JUSTIFIED'
    ALERT_STATUS_RESOLVED_PENALIZED = 'RESOLVED_PENALIZED'
    ALERT_STATUS_CHOICES = [
        (ALERT_STATUS_UNINVESTIGATED, 'لم يتم التحقيق (جديد)'),
        (ALERT_STATUS_UNDER_REVIEW, 'قيد المراجعة مع المزرعة'),
        (ALERT_STATUS_RESOLVED_JUSTIFIED, 'مُبرر (تمت الموافقة)'),
        (ALERT_STATUS_RESOLVED_PENALIZED, 'غير مُبرر (تم تغريم المتسبب)'),
    ]

    CATEGORY_BUDGET_OVERRUN = 'BUDGET_OVERRUN'
    CATEGORY_DIESEL_ANOMALY = 'DIESEL_ANOMALY'
    CATEGORY_LABOR_EXCESS = 'LABOR_EXCESS'
    CATEGORY_MATERIAL_WASTE = 'MATERIAL_WASTE'
    CATEGORY_SCHEDULE_DEVIATION = 'SCHEDULE_DEVIATION'
    CATEGORY_OTHER = 'OTHER'
    CATEGORY_CHOICES = [
        (CATEGORY_BUDGET_OVERRUN, 'تجاوز الميزانية'),
        (CATEGORY_DIESEL_ANOMALY, 'شبهة تلاعب بالديزل'),
        (CATEGORY_LABOR_EXCESS, 'إسراف في العمالة'),
        (CATEGORY_MATERIAL_WASTE, 'هدر مواد'),
        (CATEGORY_SCHEDULE_DEVIATION, 'انحراف عن الجدول الزمني'),
        (CATEGORY_OTHER, 'أخرى'),
    ]

    farm = models.ForeignKey(
        'core.Farm',
        on_delete=models.CASCADE,
        related_name='variance_alerts',
    )
    daily_log = models.ForeignKey(
        'core.DailyLog',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shadow_variance_alerts',
    )

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default=CATEGORY_BUDGET_OVERRUN,
        db_index=True,
    )
    activity_name = models.CharField(
        max_length=255,
        help_text="اسم العملية التي حدث فيها التجاوز (مثال: حراثة)",
    )

    # YECO Financial Doctrine: Decimal(19, 4) exclusively
    planned_cost = models.DecimalField(
        max_digits=19, decimal_places=4, default=Decimal('0.0000'),
    )
    actual_cost = models.DecimalField(
        max_digits=19, decimal_places=4, default=Decimal('0.0000'),
    )
    variance_amount = models.DecimalField(
        max_digits=19, decimal_places=4,
        help_text="مبلغ الهدر (الفعلي − المخطط)",
    )
    variance_percentage = models.DecimalField(
        max_digits=7, decimal_places=2,
        help_text="نسبة التجاوز المئوية",
    )

    alert_message = models.TextField(
        help_text="رسالة الإنذار التفصيلية للإدارة",
    )
    status = models.CharField(
        max_length=25,
        choices=ALERT_STATUS_CHOICES,
        default=ALERT_STATUS_UNINVESTIGATED,
        db_index=True,
    )
    resolved_by = models.ForeignKey(
        'auth.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'core_variancealert'
        ordering = ['-created_at']
        verbose_name = "إنذار انحراف الخطة"
        verbose_name_plural = "إنذارات انحراف الخطة"
        indexes = [
            models.Index(fields=['farm', 'status']),
            models.Index(fields=['category']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"[{self.farm}] {self.activity_name} — تجاوز: {self.variance_percentage}%"
