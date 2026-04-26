import uuid
from django.db import models
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from django.core.validators import FileExtensionValidator # التحقق من الصلاحية (الجولة 18)
import mimetypes
from django.core.exceptions import ValidationError
from .base import SoftDeleteModel
from .farm import Farm, Location, Asset
from .settings import Supervisor
# from .inventory import Item, Unit # Removed to fix Circular Import

class AuditLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    actor = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.DO_NOTHING, db_constraint=False)
    farm = models.ForeignKey('core.Farm', null=True, blank=True, on_delete=models.DO_NOTHING, db_constraint=False)
    action = models.CharField(max_length=100) # Increased for UI_ROUTE_BREACH_ATTEMPT support
    model = models.CharField(max_length=100)
    object_id = models.CharField(max_length=500) # Increased for long URL audit support

    new_payload = models.JSONField(default=dict, blank=True)
    old_payload = models.JSONField(default=dict, blank=True, help_text="State before mutation for forensic diff")
    reason = models.CharField(max_length=500, blank=True, default="", help_text="Mandatory explanation for sensitive changes")
    signature = models.CharField(max_length=512, blank=True, null=True, help_text="Cryptographic HMAC-SHA512 record signature")


    @property
    def payload(self):
        """Backward-compatible alias (legacy/tests expect AuditLog.payload)."""
        return self.new_payload

    @payload.setter
    def payload(self, value):
        # Keep semantics: mutation only becomes effective if saved; save() forbids updates.
        self.new_payload = value


    def __str__(self):
        return f"[{self.timestamp}] {self.actor} {self.action} {self.model}:{self.object_id}"

    class Meta:
        verbose_name = "سجل تدقيق"
        verbose_name_plural = "سجلات التدقيق"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("AuditLog is append-only; updates are not allowed.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("AuditLog is append-only; deletes are not allowed.")

class Attachment(SoftDeleteModel):
    EVIDENCE_CLASS_TRANSIENT = "transient"
    EVIDENCE_CLASS_OPERATIONAL = "operational"
    EVIDENCE_CLASS_FINANCIAL = "financial_record"
    EVIDENCE_CLASS_LEGAL_HOLD = "legal_hold"
    EVIDENCE_CLASS_CHOICES = [
        (EVIDENCE_CLASS_TRANSIENT, "مؤقت/مسودة"),
        (EVIDENCE_CLASS_OPERATIONAL, "تشغيلي"),
        (EVIDENCE_CLASS_FINANCIAL, "سجل مالي حاكم"),
        (EVIDENCE_CLASS_LEGAL_HOLD, "حجز قانوني/تدقيقي"),
    ]
    STORAGE_TIER_HOT = "hot"
    STORAGE_TIER_WARM = "warm"
    STORAGE_TIER_ARCHIVE = "archive"
    STORAGE_TIER_CHOICES = [
        (STORAGE_TIER_HOT, "Hot"),
        (STORAGE_TIER_WARM, "Warm"),
        (STORAGE_TIER_ARCHIVE, "Archive"),
    ]
    MALWARE_SCAN_PENDING = "pending"
    MALWARE_SCAN_PASSED = "passed"
    MALWARE_SCAN_QUARANTINED = "quarantined"
    MALWARE_SCAN_CHOICES = [
        (MALWARE_SCAN_PENDING, "Pending"),
        (MALWARE_SCAN_PASSED, "Passed"),
        (MALWARE_SCAN_QUARANTINED, "Quarantined"),
    ]

    file = models.FileField(
        upload_to="attachments/%Y/%m/%d", 
        max_length=100,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'csv', 'xlsx'])] # أمان (الجولة 18)
    )
    name = models.CharField(max_length=200, blank=True, default="")
    size = models.IntegerField(default=0)
    content_type = models.CharField(max_length=120, blank=True, default="")
    evidence_class = models.CharField(max_length=24, choices=EVIDENCE_CLASS_CHOICES, default=EVIDENCE_CLASS_OPERATIONAL)
    is_authoritative_evidence = models.BooleanField(default=False)
    sha256_checksum = models.CharField(max_length=64, blank=True, default="")
    expires_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    storage_tier = models.CharField(max_length=16, choices=STORAGE_TIER_CHOICES, default=STORAGE_TIER_HOT)
    archive_backend = models.CharField(max_length=24, blank=True, default="filesystem")
    archive_key = models.CharField(max_length=255, blank=True, default="")
    malware_scan_status = models.CharField(max_length=20, choices=MALWARE_SCAN_CHOICES, default=MALWARE_SCAN_PENDING)
    quarantine_reason = models.CharField(max_length=255, blank=True, default="")
    scanned_at = models.DateTimeField(null=True, blank=True)
    quarantined_at = models.DateTimeField(null=True, blank=True)
    restored_at = models.DateTimeField(null=True, blank=True)

    # ------------------------------------------------------------------
    # V21 Attachment Policy Matrix metadata (docs/reference/ATTACHMENT_POLICY_MATRIX_V21.yaml)
    # ------------------------------------------------------------------
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="uploaded_attachments",
        help_text="User who uploaded the attachment (required by policy).",
    )
    farm = models.ForeignKey(
        Farm,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="attachments",
        help_text="Farm scope for isolation/RLS (required by policy when applicable).",
    )
    document_scope = models.CharField(
        max_length=120,
        blank=True,
        default="",
        help_text="Fallback scope when not tied to a single farm row (required if farm is null).",
    )
    related_document_type = models.CharField(
        max_length=80,
        blank=True,
        default="",
        help_text="Type of business document this attachment supports (required by policy).",
    )

    attachment_class = models.CharField(
        max_length=24,
        choices=EVIDENCE_CLASS_CHOICES,
        default=EVIDENCE_CLASS_OPERATIONAL,
        help_text="Policy attachment class (mirrors evidence_class; required).",
    )
    retention_class = models.CharField(
        max_length=24,
        choices=EVIDENCE_CLASS_CHOICES,
        default=EVIDENCE_CLASS_OPERATIONAL,
        help_text="Retention class (required by policy; typically equals attachment_class).",
    )
    ARCHIVE_STATE_HOT = "hot"
    ARCHIVE_STATE_ARCHIVED = "archived"
    ARCHIVE_STATE_PURGED = "purged"
    ARCHIVE_STATE_CHOICES = [
        (ARCHIVE_STATE_HOT, "Hot"),
        (ARCHIVE_STATE_ARCHIVED, "Archived"),
        (ARCHIVE_STATE_PURGED, "Purged"),
    ]
    archive_state = models.CharField(
        max_length=24,
        choices=ARCHIVE_STATE_CHOICES,
        default=ARCHIVE_STATE_HOT,
        help_text="Archive lifecycle state (required by policy).",
    )
    scan_state = models.CharField(
        max_length=20,
        choices=MALWARE_SCAN_CHOICES,
        default=MALWARE_SCAN_PENDING,
        help_text="Scan lifecycle state (mirrors malware_scan_status; required).",
    )
    QUARANTINE_STATE_NONE = "none"
    QUARANTINE_STATE_QUARANTINED = "quarantined"
    QUARANTINE_STATE_RESTORED = "restored"
    QUARANTINE_STATE_CHOICES = [
        (QUARANTINE_STATE_NONE, "None"),
        (QUARANTINE_STATE_QUARANTINED, "Quarantined"),
        (QUARANTINE_STATE_RESTORED, "Restored"),
    ]
    quarantine_state = models.CharField(
        max_length=24,
        choices=QUARANTINE_STATE_CHOICES,
        default=QUARANTINE_STATE_NONE,
        help_text="Quarantine lifecycle state (required by policy).",
    )

    filename_original = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Original filename as uploaded by client (required by policy).",
    )
    mime_type_detected = models.CharField(
        max_length=120,
        blank=True,
        default="",
        help_text="Detected MIME type (required by policy).",
    )
    size_bytes = models.BigIntegerField(
        default=0,
        help_text="Size in bytes (required by policy).",
    )
    content_hash = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="SHA-256 hash (required by policy; mirrors sha256_checksum).",
    )
    authoritative_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when marked authoritative (required when applicable).",
    )


    class Meta:
        verbose_name = "مرفق"
        verbose_name_plural = "المرفقات"

    def _sync_v21_metadata(self):
        """Keep V21 metadata fields consistent with legacy fields."""
        # Mirror legacy -> V21
        if self.evidence_class and self.attachment_class != self.evidence_class:
            self.attachment_class = self.evidence_class
        if not self.retention_class:
            self.retention_class = self.attachment_class or self.EVIDENCE_CLASS_OPERATIONAL

        if self.sha256_checksum and self.content_hash != self.sha256_checksum:
            self.content_hash = self.sha256_checksum
        if self.content_type and self.mime_type_detected != self.content_type:
            self.mime_type_detected = self.content_type
        if self.size and self.size_bytes != self.size:
            self.size_bytes = int(self.size)

        # Scan/quarantine state mirrors
        if self.malware_scan_status and self.scan_state != self.malware_scan_status:
            self.scan_state = self.malware_scan_status

        if self.malware_scan_status == self.MALWARE_SCAN_QUARANTINED:
            self.quarantine_state = self.QUARANTINE_STATE_QUARANTINED
        elif self.restored_at is not None:
            self.quarantine_state = self.QUARANTINE_STATE_RESTORED
        else:
            self.quarantine_state = self.QUARANTINE_STATE_NONE

        # Archive state mirrors
        if self.storage_tier == self.STORAGE_TIER_ARCHIVE:
            self.archive_state = self.ARCHIVE_STATE_ARCHIVED
        elif self.deleted_at is not None:
            self.archive_state = self.ARCHIVE_STATE_PURGED
        else:
            self.archive_state = self.ARCHIVE_STATE_HOT

        # Authoritative timestamp
        if self.is_authoritative_evidence and self.authoritative_at is None:
            self.authoritative_at = self.archived_at or timezone.now()

    def _validate_required_v21_metadata(self):
        missing = []
        # required by policy
        if not self.uploaded_by_id:
            missing.append("uploaded_by")
        if not (self.farm_id or (self.document_scope and self.document_scope.strip())):
            missing.append("farm_id_or_document_scope")
        if not (self.related_document_type and self.related_document_type.strip()):
            missing.append("related_document_type")
        if not (self.filename_original and self.filename_original.strip()):
            missing.append("filename_original")
        if not (self.mime_type_detected and self.mime_type_detected.strip()):
            missing.append("mime_type_detected")
        if not (self.content_hash and self.content_hash.strip()):
            missing.append("content_hash")
        if not self.size_bytes:
            missing.append("size_bytes")
        if not self.attachment_class:
            missing.append("attachment_class")
        if not self.retention_class:
            missing.append("retention_class")
        if not self.archive_state:
            missing.append("archive_state")
        if not self.scan_state:
            missing.append("scan_state")
        if not self.quarantine_state:
            missing.append("quarantine_state")
        if self.is_authoritative_evidence and self.authoritative_at is None:
            missing.append("authoritative_at_when_applicable")
        if missing:
            raise ValidationError({ "metadata": f"Missing required attachment metadata: {', '.join(missing)}"})

    def clean(self):

        super().clean()
        if self.is_authoritative_evidence and self.evidence_class == self.EVIDENCE_CLASS_TRANSIENT:
            raise ValidationError("لا يمكن وسم مستند حاكم كسجل مؤقت.")
        if self.evidence_class == self.EVIDENCE_CLASS_LEGAL_HOLD and self.expires_at is not None:
            raise ValidationError("المرفقات تحت legal hold لا يجوز إعطاؤها تاريخ حذف.")
        if self.malware_scan_status == self.MALWARE_SCAN_QUARANTINED and not self.quarantine_reason:
            raise ValidationError("سبب الحجر مطلوب عند وسم الملف كمشبوه.")
        if self.archive_key and not self.archive_backend:
            raise ValidationError("archive_backend مطلوب عند تحديد archive_key.")

    def save(self, *args, **kwargs):
        import hashlib
        from django.utils import timezone as dj_timezone
        from datetime import timedelta
        if self.file and hasattr(self.file, "size"):
            self.size = self.file.size
        if self.file and not self.name:
            self.name = getattr(self.file, "name", "") or self.name
        if self.file and not self.content_type:
            guessed, _ = mimetypes.guess_type(getattr(self.file, "name", ""))
            self.content_type = guessed or self.content_type
        if self.file and hasattr(self.file, "open"):
            try:
                pos = self.file.tell() if hasattr(self.file, "tell") else None
                self.file.open("rb")
                self.sha256_checksum = hashlib.sha256(self.file.read()).hexdigest()
                if pos is not None:
                    self.file.seek(pos)
            except (OSError, ValueError, AttributeError):
                # checksum best-effort only; model validation remains strict elsewhere
                pass
        if self.evidence_class == self.EVIDENCE_CLASS_TRANSIENT and self.expires_at is None:
            self.expires_at = dj_timezone.now() + timedelta(days=30)
        if self.archived_at and self.archived_at <= dj_timezone.now() and self.archive_key:
            self.storage_tier = self.STORAGE_TIER_ARCHIVE
        if self.malware_scan_status == self.MALWARE_SCAN_QUARANTINED:
            self.storage_tier = self.STORAGE_TIER_HOT
            if self.quarantined_at is None:
                self.quarantined_at = dj_timezone.now()
        # V21 policy metadata sync + enforcement
        self._sync_v21_metadata()
        self._validate_required_v21_metadata()
        super().save(*args, **kwargs)



class AttachmentLifecycleEvent(models.Model):
    ACTION_RECEIVED = "received"
    ACTION_SCAN_PASSED = "scan_passed"
    ACTION_SCAN_QUARANTINED = "scan_quarantined"
    ACTION_AUTHORITATIVE_MARKED = "authoritative_marked"
    ACTION_LEGAL_HOLD_APPLIED = "legal_hold_applied"
    ACTION_LEGAL_HOLD_RELEASED = "legal_hold_released"
    ACTION_ARCHIVED = "archived"
    ACTION_RESTORED = "restored"
    ACTION_PURGED = "purged"
    ACTION_CHOICES = [
        (ACTION_RECEIVED, "Received"),
        (ACTION_SCAN_PASSED, "Scan Passed"),
        (ACTION_SCAN_QUARANTINED, "Scan Quarantined"),
        (ACTION_AUTHORITATIVE_MARKED, "Authoritative Marked"),
        (ACTION_LEGAL_HOLD_APPLIED, "Legal Hold Applied"),
        (ACTION_LEGAL_HOLD_RELEASED, "Legal Hold Released"),
        (ACTION_ARCHIVED, "Archived"),
        (ACTION_RESTORED, "Restored"),
        (ACTION_PURGED, "Purged"),
    ]

    attachment = models.ForeignKey('core.Attachment', on_delete=models.CASCADE, related_name='lifecycle_events')
    actor = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='attachment_lifecycle_events')
    action = models.CharField(max_length=40, choices=ACTION_CHOICES)
    note = models.CharField(max_length=255, blank=True, default='')
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'core_attachmentlifecycleevent'
        verbose_name = 'حدث دورة حياة مرفق'
        verbose_name_plural = 'أحداث دورة حياة المرفقات'
        ordering = ['created_at']

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError('AttachmentLifecycleEvent is append-only; updates are not allowed.')
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('AttachmentLifecycleEvent is append-only; deletes are not allowed.')


class DailyLog(SoftDeleteModel):
    def __init__(self, *args, **kwargs):
        legacy_date = kwargs.pop("date", None)
        legacy_note = kwargs.pop("note", None)
        if legacy_date is not None and "log_date" not in kwargs:
            kwargs["log_date"] = legacy_date
        if legacy_note is not None and "notes" not in kwargs:
            kwargs["notes"] = legacy_note
        super().__init__(*args, **kwargs)

    from smart_agri.core.constants import DailyLogStatus
    STATUS_DRAFT = DailyLogStatus.DRAFT
    STATUS_SUBMITTED = DailyLogStatus.SUBMITTED
    STATUS_APPROVED = DailyLogStatus.APPROVED
    STATUS_REJECTED = DailyLogStatus.REJECTED
    
    # Use Enum directly
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="daily_logs")
    supervisor = models.ForeignKey(Supervisor, null=True, blank=True, on_delete=models.SET_NULL, related_name="daily_logs")
    log_date = models.DateField(db_index=True)
    
    # [Offline Hardening] Client-Side ID for Sync
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    # [AGRI-GUARDIAN] Explicit Request ID for Retry Logic (SQL Patch Sync)
    mobile_request_id = models.CharField(max_length=64, null=True, blank=True, unique=True, help_text="Frontend Request ID for Idempotency")
    
    device_timestamp = models.DateTimeField(
        null=True, blank=True,
        help_text="Timestamp from field device (for offline reconciliation)"
    )
    
    status = models.CharField(
        max_length=50, 
        default=DailyLogStatus.DRAFT, 
        choices=DailyLogStatus.choices, 
        db_index=True
    )
    notes = models.TextField(blank=True, null=True)
    observation_data = models.JSONField(default=dict, blank=True)

    # [Forensic Axis] Sovereign Proof and Signature (Axis 21.F)
    eternity_proof_id = models.UUIDField(null=True, blank=True, help_text="Permanent forensic evidence bundle ID")
    sovereign_signature = models.CharField(max_length=512, blank=True, null=True, help_text="Cryptographic chain signature")

    # [Axis 26: Tree GIS] Location Evidence
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    gps_accuracy = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="Accuracy in meters")

    
    # حقول سير عمل الاعتماد
    approved_by = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='daily_logs_approved')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")
    variance_status = models.CharField(
        max_length=20,
        default="OK",
        db_index=True,
        choices=(
            ("OK", "OK"),
            ("WARNING", "WARNING"),
            ("CRITICAL", "CRITICAL"),
        ),
    )
    variance_note = models.TextField(blank=True, default="")
    variance_approved_by = models.ForeignKey(
        'auth.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='daily_logs_variance_approved',
    )
    variance_approved_at = models.DateTimeField(null=True, blank=True)
    # Diesel monitoring alerts
    FUEL_ALERT_STATUS_OK = "OK"
    FUEL_ALERT_STATUS_WARNING = "WARNING"
    FUEL_ALERT_STATUS_CRITICAL = "CRITICAL"
    FUEL_ALERT_STATUS_CHOICES = [
        (FUEL_ALERT_STATUS_OK, "OK"),
        (FUEL_ALERT_STATUS_WARNING, "Warning"),
        (FUEL_ALERT_STATUS_CRITICAL, "Critical"),
    ]
    fuel_alert_status = models.CharField(
        max_length=20,
        choices=FUEL_ALERT_STATUS_CHOICES,
        default=FUEL_ALERT_STATUS_OK,
        db_index=True,
    )
    fuel_alert_note = models.TextField(blank=True, default="")
    fuel_alert_approved_by = models.ForeignKey(
        'auth.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='daily_logs_fuel_alert_approvals',
    )
    fuel_alert_approved_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='daily_logs_created')
    updated_by = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='daily_logs_updated')

    # [AGRI-GUARDIAN] State Machine — valid status transitions.
    VALID_TRANSITIONS = {
        DailyLogStatus.DRAFT: {DailyLogStatus.SUBMITTED},
        DailyLogStatus.SUBMITTED: {DailyLogStatus.APPROVED, DailyLogStatus.REJECTED},
        DailyLogStatus.APPROVED: set(),  # Terminal state — no further transitions
        DailyLogStatus.REJECTED: {DailyLogStatus.DRAFT},  # Can revert to draft for correction
    }

    class Meta:
        managed = True
        db_table = 'core_dailylog'
        verbose_name = "يومية عمل"
        verbose_name_plural = "يوميات العمل"
        indexes = [
            models.Index(fields=['farm', 'log_date'], name='idx_dailylog_farm_date'),
            models.Index(fields=['log_date'], name='idx_dailylog_date_only'),
            models.Index(fields=['fuel_alert_status'], name='idx_dailylog_fuel_alert_status'),
        ]
        ordering = ['-log_date']

    @property
    def date(self):
        return self.log_date

    @date.setter
    def date(self, value):
        self.log_date = value

    @property
    def note(self):
        return self.notes

    @note.setter
    def note(self, value):
        self.notes = value

    def save(self, *args, **kwargs):
        # [AGRI-GUARDIAN §Axis-6] Strict Tenant Isolation Enforcement.
        if not self.farm_id:
            raise ValidationError(
                "[AGRI-GUARDIAN] farm_id مطلوب لكل يومية عمل (DailyLog). "
                "انتهاك عزل المزرعة — يُمنع نشر سجل بدون نطاق مزرعة محدد."
            )

        # [AGRI-GUARDIAN] State Machine Guard — enforce valid status transitions.
        if self.pk is not None:
            try:
                old = DailyLog.objects.only("status").get(pk=self.pk)
                old_status = old.status
                new_status = self.status
                if old_status != new_status:
                    allowed = self.VALID_TRANSITIONS.get(old_status, set())
                    if new_status not in allowed:
                        raise ValidationError(
                            f"[AGRI-GUARDIAN] انتقال حالة غير مسموح: {old_status} → {new_status}. "
                            f"الانتقالات المسموحة من {old_status}: {allowed or 'لا يوجد (حالة نهائية)'}."
                        )
            except DailyLog.DoesNotExist:
                pass  # New record or race condition — allow save
        
        is_new = self.pk is None
        super().save(*args, **kwargs)

        # [AGRI-GUARDIAN §Axis-11] Evaluate Tree Census upon creation
        if is_new:
            pass


    def _sync_v21_metadata(self):
        """Keep V21 metadata fields consistent with legacy fields."""
        # Mirror legacy -> V21
        if self.evidence_class and self.attachment_class != self.evidence_class:
            self.attachment_class = self.evidence_class
        if not self.retention_class:
            self.retention_class = self.attachment_class or self.EVIDENCE_CLASS_OPERATIONAL

        if self.sha256_checksum and self.content_hash != self.sha256_checksum:
            self.content_hash = self.sha256_checksum
        if self.content_type and self.mime_type_detected != self.content_type:
            self.mime_type_detected = self.content_type
        if self.size and self.size_bytes != self.size:
            self.size_bytes = int(self.size)

        # Scan/quarantine state mirrors
        if self.malware_scan_status and self.scan_state != self.malware_scan_status:
            self.scan_state = self.malware_scan_status

        if self.malware_scan_status == self.MALWARE_SCAN_QUARANTINED:
            self.quarantine_state = self.QUARANTINE_STATE_QUARANTINED
        elif self.restored_at is not None:
            self.quarantine_state = self.QUARANTINE_STATE_RESTORED
        else:
            self.quarantine_state = self.QUARANTINE_STATE_NONE

        # Archive state mirrors
        if self.storage_tier == self.STORAGE_TIER_ARCHIVE:
            self.archive_state = self.ARCHIVE_STATE_ARCHIVED
        elif self.deleted_at is not None:
            self.archive_state = self.ARCHIVE_STATE_PURGED
        else:
            self.archive_state = self.ARCHIVE_STATE_HOT

        # Authoritative timestamp
        if self.is_authoritative_evidence and self.authoritative_at is None:
            self.authoritative_at = self.archived_at or timezone.now()

    def _validate_required_v21_metadata(self):
        missing = []
        # required by policy
        if not self.uploaded_by_id:
            missing.append("uploaded_by")
        if not (self.farm_id or (self.document_scope and self.document_scope.strip())):
            missing.append("farm_id_or_document_scope")
        if not (self.related_document_type and self.related_document_type.strip()):
            missing.append("related_document_type")
        if not (self.filename_original and self.filename_original.strip()):
            missing.append("filename_original")
        if not (self.mime_type_detected and self.mime_type_detected.strip()):
            missing.append("mime_type_detected")
        if not (self.content_hash and self.content_hash.strip()):
            missing.append("content_hash")
        if not self.size_bytes:
            missing.append("size_bytes")
        if not self.attachment_class:
            missing.append("attachment_class")
        if not self.retention_class:
            missing.append("retention_class")
        if not self.archive_state:
            missing.append("archive_state")
        if not self.scan_state:
            missing.append("scan_state")
        if not self.quarantine_state:
            missing.append("quarantine_state")
        if self.is_authoritative_evidence and self.authoritative_at is None:
            missing.append("authoritative_at_when_applicable")
        if missing:
            raise ValidationError({ "metadata": f"Missing required attachment metadata: {', '.join(missing)}"})

    def clean(self):

        super().clean()
        forbidden_keys = [
            'sensor_id',
            'device_id',
            'telemetry',
            'battery_level',
            'gps_trace',
            'auto_reading',
        ]
        if self.observation_data:
            keys = self.observation_data.keys()
            found_forbidden = [
                key for key in keys if any(bad in key.lower() for bad in forbidden_keys)
            ]
            if found_forbidden:
                raise ValidationError(
                    "IoT/Automated data detected in manual log: "
                    f"{found_forbidden}. This system strictly enforces Manual Entry."
                )
        if self.fuel_alert_status not in {self.FUEL_ALERT_STATUS_OK,
                                          self.FUEL_ALERT_STATUS_WARNING,
                                          self.FUEL_ALERT_STATUS_CRITICAL}:
            raise ValidationError("Invalid fuel alert status.")

class FuelConsumptionAlert(models.Model):
    STATUS_OK = "OK"
    STATUS_WARNING = "WARNING"
    STATUS_CRITICAL = "CRITICAL"
    STATUS_CHOICES = [
        (STATUS_OK, "OK"),
        (STATUS_WARNING, "Warning"),
        (STATUS_CRITICAL, "Critical"),
    ]

    log = models.ForeignKey(DailyLog, on_delete=models.CASCADE, related_name="fuel_alerts")
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="fuel_alerts")
    machine_hours = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    actual_liters = models.DecimalField(max_digits=19, decimal_places=4)
    expected_liters = models.DecimalField(max_digits=19, decimal_places=4)
    deviation_pct = models.DecimalField(max_digits=6, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OK)
    note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "core_fuelconsumptionalert"
        verbose_name = "تنبيه استهلاك الوقود"
        verbose_name_plural = "تنبيهات استهلاك الوقود"
        indexes = [
            models.Index(fields=["log"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.log} - {self.asset.name} - {self.status}"

class MaterialVarianceAlert(models.Model):
    """
    [AGRI-GUARDIAN] Protocol III Validation
    Logs analytical variances when actual material usage exceeds the expected
    Agronomic BOM configured in the CropRecipe.
    """
    STATUS_WARNING = "WARNING"
    STATUS_CRITICAL = "CRITICAL"
    STATUS_CHOICES = [
        (STATUS_WARNING, "Warning"),
        (STATUS_CRITICAL, "Critical"),
    ]

    log = models.ForeignKey('core.DailyLog', on_delete=models.CASCADE, related_name="material_alerts")
    crop_plan = models.ForeignKey('core.CropPlan', on_delete=models.CASCADE, related_name="material_alerts")
    item = models.ForeignKey('inventory.Item', on_delete=models.PROTECT, related_name="material_alerts")
    actual_qty = models.DecimalField(max_digits=19, decimal_places=4)
    expected_qty = models.DecimalField(max_digits=19, decimal_places=4)
    deviation_pct = models.DecimalField(max_digits=6, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_WARNING)
    note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "core_materialvariancealert"
        verbose_name = "تنبيه انحراف المواد (BOM)"
        verbose_name_plural = "تنبيهات انحراف المواد (BOM)"
        indexes = [
            models.Index(fields=["log"]),
            models.Index(fields=["status"]),
            models.Index(fields=["crop_plan"]),
        ]

    def __str__(self):
        return f"[{self.status}] {self.crop_plan} - {self.item.name}: {self.deviation_pct}% Variance"

class IdempotencyRecord(models.Model):
    STATUS_IN_PROGRESS = 'IN_PROGRESS'
    STATUS_SUCCEEDED = 'SUCCEEDED'
    STATUS_FAILED = 'FAILED'
    STATUS_CHOICES = [
        (STATUS_IN_PROGRESS, 'Processing'),
        (STATUS_SUCCEEDED, 'Succeeded'),
        (STATUS_FAILED, 'Failed'),
    ]

    key = models.CharField(max_length=80, db_index=True)
    user = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL)
    farm = models.ForeignKey(Farm, null=True, blank=True, on_delete=models.SET_NULL)
    
    # Scope Definition
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=200)
    
    # Payload Integrity
    request_hash = models.CharField(max_length=64, blank=True, null=True, help_text="SHA256(method+path+body+params)")
    
    # Lock State
    status = models.CharField(max_length=20, default=STATUS_IN_PROGRESS, choices=STATUS_CHOICES, db_index=True)
    expiry_at = models.DateTimeField(null=True, blank=True, help_text="Lock expiration for IN_PROGRESS")

    # Access Audit
    model = models.CharField(max_length=100)
    object_id = models.CharField(max_length=50)
    
    # Response Cache
    response_status = models.PositiveSmallIntegerField(null=True, blank=True)
    response_body = models.JSONField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # V2: Scope is (User + Key + Endpoint Scope)
        unique_together = ('user', 'key', 'method', 'path')
        constraints = [
            models.UniqueConstraint(
                fields=['key', 'method', 'path'],
                condition=models.Q(user__isnull=True),
                name='unique_anonymous_idempotency_key'
            )
        ]
        indexes = [
            models.Index(fields=['user', 'key', 'method', 'path']),
            models.Index(fields=['status']),
            models.Index(fields=['expiry_at']),
        ]

class SyncRecord(models.Model):
    from smart_agri.core.constants import SyncStatus, SyncCategory
    STATUS_PENDING = SyncStatus.PENDING
    STATUS_SUCCESS = SyncStatus.SUCCESS
    STATUS_FAILED = SyncStatus.FAILED
    CATEGORY_DAILY_LOG = SyncCategory.DAILY_LOG
    CATEGORY_HTTP_REQUEST = SyncCategory.HTTP_REQUEST
    # Legacy alias expected by old tests.
    CATEGORY_HTTP = SyncCategory.HTTP_REQUEST

    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='sync_records')
    farm = models.ForeignKey(Farm, null=True, blank=True, on_delete=models.SET_NULL, related_name='sync_records')
    category = models.CharField(max_length=40, default=SyncCategory.DAILY_LOG, choices=SyncCategory.choices)
    reference = models.CharField(max_length=100, blank=True, default="")
    status = models.CharField(max_length=12, choices=SyncStatus.choices, default=SyncStatus.PENDING)

    attempt_count = models.PositiveIntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    last_error_message = models.TextField(blank=True, default="")
    payload = models.JSONField(default=dict, blank=True)
    log_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = "سجل التزامن"
        verbose_name_plural = "سجلات التزامن"
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['category', 'reference']),
            models.Index(fields=['log_date']),
        ]

    def mark(self, status, message=None):
        self.status = status
        if message:
            self.last_error_message = message
        self.attempt_count += 1
        self.last_attempt_at = timezone.now()
        self.save(update_fields=['status', 'last_error_message', 'attempt_count', 'last_attempt_at', 'updated_at'])
