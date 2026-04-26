from django.conf import settings
from django.db import models


class OpsAlertReceipt(models.Model):
    STATUS_ACKNOWLEDGED = "acknowledged"
    STATUS_SNOOZED = "snoozed"
    STATUS_CHOICES = [
        (STATUS_ACKNOWLEDGED, "Acknowledged"),
        (STATUS_SNOOZED, "Snoozed"),
    ]

    fingerprint = models.CharField(max_length=255, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ops_alert_receipts",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    snooze_until = models.DateTimeField(null=True, blank=True)
    note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "core_ops_alert_receipt"
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["fingerprint", "actor"],
                name="core_opsalertreceipt_actor_fingerprint_uniq",
            )
        ]
        indexes = [
            models.Index(fields=["actor", "status"], name="core_opsalert_actor_status_idx"),
            models.Index(fields=["actor", "snooze_until"], name="core_opsalert_actor_snooze_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.fingerprint}:{self.actor_id}:{self.status}"
