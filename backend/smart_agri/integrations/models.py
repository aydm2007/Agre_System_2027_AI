
from django.db import models
from django.conf import settings

class WebhookEndpoint(models.Model):
    EVENT_CHOICES = [
        ("create","create"),
        ("update","update"),
        ("delete","delete"),
        ("audit","audit"),
    ]
    name = models.CharField(max_length=150)
    event = models.CharField(max_length=20, choices=EVENT_CHOICES, default="audit")
    url = models.URLField()
    secret = models.CharField(max_length=200, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"{self.name} ({self.event})"

class OutboundDelivery(models.Model):
    endpoint = models.ForeignKey(WebhookEndpoint, on_delete=models.CASCADE, related_name="deliveries")
    status = models.CharField(max_length=20, default="pending")  # pending/sent/failed
    response_code = models.IntegerField(null=True, blank=True)
    response_text = models.TextField(blank=True, default="")
    attempts = models.IntegerField(default=0)
    last_attempt = models.DateTimeField(null=True, blank=True)
    # Round 17: Head-of-Line Blocking Fix
    next_attempt_at = models.DateTimeField(null=True, blank=True, db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"Delivery {self.id} -> {self.endpoint.name} [{self.status}]"

class ImportLog(models.Model):
    source = models.CharField(max_length=100, default="webhook")
    status = models.CharField(max_length=20, default="received")
    payload = models.JSONField(default=dict, blank=True)
    headers = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    response_code = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    error_message = models.TextField(blank=True, default="")
    
    def __str__(self):
        return f"ImportLog {self.id} from {self.source} - {self.status}"


class ExternalFinanceBatch(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_EXPORTED = "exported"
    STATUS_ACK = "acknowledged"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_EXPORTED, "Exported"),
        (STATUS_ACK, "Acknowledged"),
        (STATUS_FAILED, "Failed"),
    ]

    farm = models.ForeignKey("core.Farm", on_delete=models.CASCADE, related_name="external_finance_batches")
    period_start = models.DateField()
    period_end = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)
    external_ref = models.CharField(max_length=120, blank=True, default="")
    checksum = models.CharField(max_length=64, blank=True, default="")
    total_debit = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    total_credit = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    payload = models.JSONField(default=dict, blank=True)
    exported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="external_finance_batches_exported"
    )
    exported_at = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "integrations_externalfinancebatch"
        indexes = [
            models.Index(fields=["farm", "period_start", "period_end"]),
            models.Index(fields=["status", "created_at"]),
        ]


class ExternalFinanceLine(models.Model):
    batch = models.ForeignKey(ExternalFinanceBatch, on_delete=models.CASCADE, related_name="lines")
    ledger_id = models.CharField(max_length=40, db_index=True)
    account_code = models.CharField(max_length=50)
    debit = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    credit = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    description = models.CharField(max_length=255, blank=True, default="")
    currency = models.CharField(max_length=10, default="YER")
    entity_ref = models.CharField(max_length=80, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "integrations_externalfinanceline"
        indexes = [
            models.Index(fields=["batch", "ledger_id"]),
        ]
