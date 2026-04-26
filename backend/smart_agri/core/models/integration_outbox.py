from __future__ import annotations

from django.conf import settings
from django.db import models


class IntegrationOutboxEvent(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        DISPATCHED = 'dispatched', 'Dispatched'
        FAILED = 'failed', 'Failed'
        DEAD_LETTER = 'dead_letter', 'Dead letter'

    event_id = models.CharField(max_length=64, unique=True)
    event_type = models.CharField(max_length=128, db_index=True)
    aggregate_type = models.CharField(max_length=64, db_index=True)
    aggregate_id = models.CharField(max_length=64, db_index=True)
    destination = models.CharField(max_length=255, default='events')
    farm = models.ForeignKey('core.Farm', null=True, blank=True, on_delete=models.SET_NULL, related_name='integration_outbox_events')
    activity = models.ForeignKey('core.Activity', null=True, blank=True, on_delete=models.SET_NULL, related_name='integration_outbox_events')
    payload = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PENDING, db_index=True)
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=10)
    available_at = models.DateTimeField(auto_now_add=True, db_index=True)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, default='')
    locked_at = models.DateTimeField(null=True, blank=True)
    locked_by = models.CharField(max_length=128, blank=True, default='')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='created_integration_outbox_events')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_integration_outbox_event'
        verbose_name = "حدث مزامنة"
        verbose_name_plural = "أحداث المزامنة"
        ordering = ['status', 'available_at', 'id']
        indexes = [
            models.Index(fields=['status', 'available_at'], name='core_integr_status_82a9d0_idx'),
            models.Index(fields=['event_type', 'status'], name='core_integr_event_t_5b913c_idx'),
            models.Index(fields=['farm', 'status'], name='core_integr_farm_id_f10203_idx'),
        ]

    def __str__(self) -> str:
        return f"{self.event_type}:{self.aggregate_id} [{self.status}]"
