"""
SyncConflict Dead Letter Queue (DLQ) — Offline Conflict Resolution.

[AGENTS.md §Offline Sync Doctrine]
Server-side validated state is authoritative (server-wins).
Failed/conflicting mutations move here with full context.
DLQ triage owned by Central Finance or delegated authority.
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from smart_agri.core.models.base import SoftDeleteModel


class SyncConflictDLQ(SoftDeleteModel):
    """
    Dead Letter Queue for offline sync conflicts.

    When a mobile/offline client submits a mutation that conflicts with
    server-validated state, the failed mutation is captured here with
    full context for manual adjudication.

    [Axis 6] farm_id is mandatory for tenant isolation.
    [Axis 7] Append-only — resolved conflicts are marked, never deleted.
    """

    STATUS_CHOICES = [
        ('PENDING', 'قيد المراجعة'),
        ('RESOLVED', 'تمت المعالجة'),
        ('REJECTED', 'مرفوض'),
        ('REPLAYED', 'أعيد تشغيله'),
    ]

    CONFLICT_TYPE_CHOICES = [
        ('DUPLICATE_IDEMPOTENCY', 'مفتاح تكراري'),
        ('FISCAL_PERIOD_CLOSED', 'فترة مالية مغلقة'),
        ('STALE_VERSION', 'إصدار قديم'),
        ('VALIDATION_FAILURE', 'خطأ في التحقق'),
        ('RLS_VIOLATION', 'انتهاك عزل البيانات'),
        ('OTHER', 'أخرى'),
    ]

    # --- Context Fields ---
    farm = models.ForeignKey(
        'core.Farm',
        on_delete=models.CASCADE,
        related_name='sync_conflicts',
        help_text="المزرعة المرتبطة بالتعارض"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sync_conflicts',
        help_text="المستخدم الذي أرسل العملية المتعارضة"
    )

    # --- Conflict Details ---
    conflict_type = models.CharField(
        max_length=30,
        choices=CONFLICT_TYPE_CHOICES,
        default='OTHER',
        help_text="نوع التعارض"
    )
    conflict_reason = models.TextField(
        help_text="وصف تفصيلي لسبب التعارض"
    )
    endpoint = models.CharField(
        max_length=255,
        help_text="API endpoint الذي وقع فيه التعارض"
    )
    http_method = models.CharField(
        max_length=10,
        default='POST',
        help_text="HTTP method"
    )

    # --- Payload ---
    request_payload = models.JSONField(
        help_text="الحمولة الأصلية من الجهاز"
    )
    idempotency_key = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        help_text="مفتاح الحدّ من التكرار"
    )

    # --- Timestamps ---
    device_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        help_text="وقت العملية على الجهاز (offline timestamp)"
    )
    server_received_at = models.DateTimeField(
        default=timezone.now,
        help_text="وقت استلام الخادم"
    )

    # --- Resolution ---
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        db_index=True,
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_sync_conflicts',
        help_text="الشخص المسؤول عن حل التعارض"
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(
        blank=True,
        default='',
        help_text="ملاحظات المعالجة"
    )

    class Meta:
        managed = True
        db_table = 'core_syncconflict_dlq'
        ordering = ['-server_received_at']
        verbose_name = "تعارض المزامنة"
        verbose_name_plural = "تعارضات المزامنة"
        indexes = [
            models.Index(fields=['farm', 'status'], name='idx_dlq_farm_status'),
            models.Index(fields=['idempotency_key'], name='idx_dlq_idemp_key'),
        ]

    def __str__(self):
        return f"DLQ#{self.pk} [{self.conflict_type}] Farm={self.farm_id} Status={self.status}"


class OfflineSyncQuarantine(SoftDeleteModel):
    """
    Axis 18 & Quarantine Rules:
    Offline payloads arriving with a device_timestamp significantly older than the
    server_timestamp that trigger a CRITICAL variance MUST be diverted to this Queue.
    
    Quarantined payloads do NOT post to the FinancialLedger or AuditLog until
    a Manager explicitly Counter-Signs.
    """

    STATUS_CHOICES = [
        ('PENDING_REVIEW', 'بانتظار مراجعة الإدارة'),
        ('APPROVED_AND_POSTED', 'تمت الموافقة والترحيل'),
        ('REJECTED', 'مرفوض نهائياً'),
    ]

    farm = models.ForeignKey(
        'core.Farm',
        on_delete=models.CASCADE,
        related_name='quarantined_payloads',
        help_text="المزرعة (لتطبيق محور العزل)"
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='quarantined_submissions',
        help_text="المسؤول الميداني الذي رفع البيانات"
    )
    
    # Financial Impact
    variance_type = models.CharField(
        max_length=50,
        help_text="نوع الانحراف الذي تسبب بالحجر (مثال: CRITICAL_BUDGET)"
    )
    device_timestamp = models.DateTimeField(
        help_text="وقت إنشاء السجل فعلياً في الحقل"
    )
    server_intercept_time = models.DateTimeField(
        default=timezone.now,
        help_text="لحظة وصول واعتراض الخادم للعملية"
    )
    
    # Payload details
    original_payload = models.JSONField(
        help_text="بيانات العملية كاملة ليتم ترحيلها عند الموافقة"
    )
    idempotency_key = models.CharField(
        max_length=255,
        db_index=True,
        help_text="المفتاح الجنائي التفادي للتكرار"
    )

    # Resolution
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='PENDING_REVIEW',
        db_index=True
    )
    manager_signature = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_quarantines',
        help_text="المدير الذي وافق على فك الحجر"
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_reason = models.TextField(
        blank=True, 
        help_text="التبرير الجنائي لفك الحجر أو الرفض"
    )

    class Meta:
        managed = True
        db_table = 'core_offlinesync_quarantine'
        ordering = ['-server_intercept_time']
        verbose_name = "حجر المزامنة المؤجلة"
        verbose_name_plural = "قوائم حجر المزامنة المؤجلة"
        indexes = [
            models.Index(fields=['farm', 'status'], name='idx_quarantine_farm_status'),
            models.Index(fields=['idempotency_key'], name='idx_quarantine_idemp'),
        ]

    def __str__(self):
        return f"Quarantine#{self.pk} [{self.variance_type}] Farm={self.farm_id} Status={self.status}"

