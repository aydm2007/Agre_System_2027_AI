
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.models import User, Permission

class FarmMembership(models.Model):
    SYSTEM_ROLES = [
        ("مدير النظام", "مدير النظام"),
    ]
    SECTOR_ROLES = [
        ("محاسب القطاع", "محاسب القطاع"),
        ("مراجع القطاع", "مراجع القطاع"),
        ("رئيس حسابات القطاع", "رئيس حسابات القطاع"),
        ("المدير المالي لقطاع المزارع", "المدير المالي لقطاع المزارع"),
        ("مدير القطاع", "مدير القطاع"),
        ("مدقق مالي", "مدقق مالي"),
    ]
    FARM_ROLES = [
        ("رئيس الحسابات", "رئيس الحسابات"),
        ("المدير المالي للمزرعة", "المدير المالي للمزرعة"),
        ("مدير المزرعة", "مدير المزرعة"),
        ("مهندس زراعي", "مهندس زراعي"),
        ("مشرف ميداني", "مشرف ميداني"),
        ("فني زراعي", "فني زراعي"),
        ("مزارع", "مزارع"),
        ("أمين مخزن", "أمين مخزن"),
        ("أمين صندوق", "أمين صندوق"),
        ("محاسب المزرعة", "محاسب المزرعة"),
        ("مدير مبيعات", "مدير مبيعات"),
        ("مسئول مشتريات", "مسئول مشتريات"),
        ("مدخل بيانات", "مدخل بيانات"),
        ("مشاهد", "مشاهد"),
    ]
    ROLE_CHOICES = SYSTEM_ROLES + SECTOR_ROLES + FARM_ROLES

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="farm_memberships")
    farm = models.ForeignKey('core.Farm', on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=60, choices=ROLE_CHOICES, default="مشاهد")
    class Meta:
        unique_together = ("user","farm")
        verbose_name = "عضوية مزرعة"
        verbose_name_plural = "عضويات المزارع"
        
    def __str__(self): return f"{self.user.username} -> {self.farm.slug} ({self.role})"
    
    @property
    def is_sector_level(self):
        """Returns True if the role is a sector-level multi-farm governance role."""
        return any(self.role == r[0] for r in self.SECTOR_ROLES)

    @property
    def is_farm_finance_lead(self):
        return self.role in {"رئيس الحسابات", "المدير المالي للمزرعة"}
    
    @property
    def is_system_level(self):
        return any(self.role == r[0] for r in self.SYSTEM_ROLES)
class PermissionTemplate(models.Model):
    name = models.CharField(max_length=80)
    slug = models.CharField(max_length=80)
    description = models.TextField()
    is_system = models.BooleanField(default=False)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Relationships inferred from SQL
    permissions = models.ManyToManyField(Permission, related_name='templates', db_table='accounts_permissiontemplate_permissions')
    users = models.ManyToManyField(User, related_name='permission_templates', db_table='accounts_permissiontemplate_users')

    class Meta:
        managed = True
        db_table = 'accounts_permissiontemplate'

class UserPermissionBinding(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='permission_bindings')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    template = models.ForeignKey(PermissionTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    source = models.CharField(max_length=16) # e.g., 'group', 'user', 'template'
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'accounts_userpermissionbinding'

class UserMFAToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mfa_tokens')
    secret = models.CharField(max_length=64)
    is_active = models.BooleanField(default=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    last_verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'accounts_usermfatoken'


class FarmGovernanceProfile(models.Model):
    TIER_SMALL = "SMALL"
    TIER_MEDIUM = "MEDIUM"
    TIER_LARGE = "LARGE"
    TIER_CHOICES = [
        (TIER_SMALL, "Small Farm"),
        (TIER_MEDIUM, "Medium Farm"),
        (TIER_LARGE, "Large Farm"),
    ]

    farm = models.OneToOneField("core.Farm", on_delete=models.CASCADE, related_name="governance_profile")
    tier = models.CharField(max_length=10, choices=TIER_CHOICES, default=TIER_SMALL)
    rationale = models.TextField(blank=True, default="")
    approved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "accounts_farmgovernanceprofile"


class RaciTemplate(models.Model):
    name = models.CharField(max_length=120, unique=True)
    tier = models.CharField(max_length=10, choices=FarmGovernanceProfile.TIER_CHOICES)
    version = models.CharField(max_length=30, default="v1")
    matrix = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    updated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "accounts_racitemplate"
        indexes = [
            models.Index(fields=["tier", "is_active"]),
        ]


class RoleDelegation(models.Model):
    principal_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="delegations_as_principal")
    delegate_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="delegations_as_delegate")
    farm = models.ForeignKey("core.Farm", on_delete=models.CASCADE, related_name="role_delegations")
    role = models.CharField(max_length=60, choices=FarmMembership.ROLE_CHOICES)
    reason = models.CharField(max_length=500)
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    approved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "accounts_roledelegation"
        indexes = [
            models.Index(fields=["farm", "role", "is_active"]),
            models.Index(fields=["delegate_user", "starts_at", "ends_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(principal_user=models.F("delegate_user")),
                name="no_self_delegation",
            ),
            models.CheckConstraint(
                check=models.Q(ends_at__gt=models.F("starts_at")),
                name="delegation_valid_window",
            ),
        ]

    def clean(self):
        super().clean()
        if self.principal_user_id == self.delegate_user_id:
            raise ValidationError("principal_user and delegate_user cannot be the same.")
        if self.ends_at <= self.starts_at:
            raise ValidationError("ends_at must be later than starts_at.")

    @property
    def is_currently_effective(self) -> bool:
        now = timezone.now()
        return self.is_active and self.starts_at <= now <= self.ends_at
