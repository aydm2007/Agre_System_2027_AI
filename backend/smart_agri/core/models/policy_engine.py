from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class PolicyPackage(models.Model):
    SCOPE_SECTOR_CENTRAL = "sector_central"
    SCOPE_CHOICES = [
        (SCOPE_SECTOR_CENTRAL, "Sector Central"),
    ]

    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True, default="")
    scope = models.CharField(max_length=40, choices=SCOPE_CHOICES, default=SCOPE_SECTOR_CENTRAL)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "core_policypackage"
        ordering = ["name"]

    def __str__(self):
        return self.name


class PolicyVersion(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_APPROVED = "approved"
    STATUS_RETIRED = "retired"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_RETIRED, "Retired"),
    ]

    package = models.ForeignKey(PolicyPackage, on_delete=models.CASCADE, related_name="versions")
    version_label = models.CharField(max_length=40)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "core_policyversion"
        ordering = ["package__name", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["package", "version_label"],
                name="uniq_policy_version_per_package",
            ),
        ]

    def clean(self):
        super().clean()
        from smart_agri.core.services.policy_engine_service import PolicyEngineService

        PolicyEngineService.validate_policy_payload(self.payload or {})

    def save(self, *args, **kwargs):
        from smart_agri.core.services.policy_engine_service import PolicyEngineService

        self.payload = PolicyEngineService.json_safe_payload(self.payload or {})
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.package.name} / {self.version_label}"


class FarmPolicyBinding(models.Model):
    farm = models.ForeignKey("core.Farm", on_delete=models.CASCADE, related_name="policy_bindings")
    policy_version = models.ForeignKey(PolicyVersion, on_delete=models.PROTECT, related_name="bindings")
    effective_from = models.DateTimeField(default=timezone.now)
    effective_to = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    reason = models.CharField(max_length=255, blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "core_farmpolicybinding"
        ordering = ["-effective_from", "-created_at"]
        indexes = [
            models.Index(fields=["farm", "is_active", "effective_from"]),
        ]

    def clean(self):
        super().clean()
        if self.effective_to and self.effective_to <= self.effective_from:
            raise ValidationError("effective_to must be later than effective_from.")

    def __str__(self):
        return f"{self.farm.name} -> {self.policy_version}"


class PolicyActivationRequest(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_APPLIED = "applied"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_APPLIED, "Applied"),
    ]

    farm = models.ForeignKey("core.Farm", on_delete=models.CASCADE, related_name="policy_activation_requests")
    policy_version = models.ForeignKey(
        PolicyVersion,
        on_delete=models.PROTECT,
        related_name="activation_requests",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    rationale = models.TextField(blank=True, default="")
    effective_from = models.DateTimeField(default=timezone.now)
    simulate_summary = models.JSONField(default=dict, blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    applied_binding = models.ForeignKey(
        FarmPolicyBinding,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="activation_requests",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "core_policyactivationrequest"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.farm.name} -> {self.policy_version} ({self.status})"


class PolicyActivationEvent(models.Model):
    ACTION_CREATED = "created"
    ACTION_SUBMITTED = "submitted"
    ACTION_APPROVED = "approved"
    ACTION_REJECTED = "rejected"
    ACTION_APPLIED = "applied"
    ACTION_CHOICES = [
        (ACTION_CREATED, "Created"),
        (ACTION_SUBMITTED, "Submitted"),
        (ACTION_APPROVED, "Approved"),
        (ACTION_REJECTED, "Rejected"),
        (ACTION_APPLIED, "Applied"),
    ]

    activation_request = models.ForeignKey(
        PolicyActivationRequest,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="events",
    )
    farm = models.ForeignKey("core.Farm", on_delete=models.CASCADE, related_name="policy_activation_events")
    policy_version = models.ForeignKey(
        PolicyVersion,
        on_delete=models.PROTECT,
        related_name="activation_events",
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    note = models.CharField(max_length=255, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "core_policyactivationevent"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.farm.name} / {self.action} / {self.policy_version}"


class PolicyExceptionRequest(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_APPLIED = "applied"
    STATUS_EXPIRED = "expired"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_APPLIED, "Applied"),
        (STATUS_EXPIRED, "Expired"),
    ]

    farm = models.ForeignKey("core.Farm", on_delete=models.CASCADE, related_name="policy_exception_requests")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    policy_fields = models.JSONField(default=list, blank=True)
    requested_patch = models.JSONField(default=dict, blank=True)
    rationale = models.TextField(blank=True, default="")
    effective_from = models.DateTimeField(default=timezone.now)
    effective_to = models.DateTimeField(null=True, blank=True)
    simulate_summary = models.JSONField(default=dict, blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    applied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "core_policyexceptionrequest"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["farm", "status", "effective_from"]),
        ]

    def clean(self):
        super().clean()
        if self.effective_to and self.effective_to <= self.effective_from:
            raise ValidationError("effective_to must be later than effective_from.")

    def __str__(self):
        return f"{self.farm.name} / exception / {self.status}"


class PolicyExceptionEvent(models.Model):
    ACTION_CREATED = "created"
    ACTION_SUBMITTED = "submitted"
    ACTION_APPROVED = "approved"
    ACTION_REJECTED = "rejected"
    ACTION_APPLIED = "applied"
    ACTION_EXPIRED = "expired"
    ACTION_CHOICES = [
        (ACTION_CREATED, "Created"),
        (ACTION_SUBMITTED, "Submitted"),
        (ACTION_APPROVED, "Approved"),
        (ACTION_REJECTED, "Rejected"),
        (ACTION_APPLIED, "Applied"),
        (ACTION_EXPIRED, "Expired"),
    ]

    exception_request = models.ForeignKey(
        PolicyExceptionRequest,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="events",
    )
    farm = models.ForeignKey("core.Farm", on_delete=models.CASCADE, related_name="policy_exception_events")
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    note = models.CharField(max_length=255, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "core_policyexceptionevent"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.farm.name} / exception / {self.action}"
