"""
[AGRI-GUARDIAN §Axis-10] Role Delegation Model.

Enables temporary transfer of authority from one user to another
within a specific farm scope. Required for RACI governance compliance.

Example: A farm Manager going on leave delegates approval authority
to a Supervisor for a defined period with an audit reason.
"""
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError

from smart_agri.core.models.base import SoftDeleteModel


class RoleDelegation(SoftDeleteModel):
    """
    نموذج التفويض المؤقت للصلاحيات.
    يسمح بنقل صلاحية محددة من مستخدم (المفوِّض) إلى آخر (المفوَّض)
    ضمن نطاق مزرعة معينة ولفترة زمنية محددة.
    """
    ROLE_CHOICES = [
        ('Manager', 'مدير المزرعة'),
        ('Admin', 'مسؤول النظام'),
        ('Supervisor', 'مشرف'),
        ('FinanceOfficer', 'مسؤول مالي'),
    ]

    principal = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='delegations_given',
        help_text='المستخدم المفوِّض (صاحب الصلاحية الأصلية)',
        verbose_name='المفوِّض',
    )
    delegate = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='delegations_received',
        help_text='المستخدم المفوَّض (الذي يستلم الصلاحية)',
        verbose_name='المفوَّض إليه',
    )
    farm = models.ForeignKey(
        'core.Farm',
        on_delete=models.CASCADE,
        # [AGRI-GUARDIAN] Use 'core_role_delegations' to avoid clash with
        # accounts.RoleDelegation.farm which already owns 'role_delegations'.
        related_name='core_role_delegations',
        help_text='المزرعة التي ينطبق عليها التفويض',
        verbose_name='المزرعة',
    )
    role = models.CharField(
        max_length=30,
        choices=ROLE_CHOICES,
        help_text='الصلاحية المفوَّضة',
        verbose_name='الصلاحية',
    )
    start_date = models.DateField(
        help_text='تاريخ بداية التفويض',
        verbose_name='من تاريخ',
    )
    end_date = models.DateField(
        help_text='تاريخ انتهاء التفويض',
        verbose_name='إلى تاريخ',
    )
    reason = models.TextField(
        help_text='سبب التفويض (إلزامي للتتبع الجنائي)',
        verbose_name='السبب',
    )
    is_active = models.BooleanField(
        default=True,
        help_text='هل التفويض فعّال حالياً',
        verbose_name='فعّال',
    )

    class Meta:
        managed = True
        db_table = 'core_role_delegation'
        verbose_name = 'تفويض صلاحيات'
        verbose_name_plural = 'تفويضات الصلاحيات'
        ordering = ['-start_date']
        constraints = [
            # No self-delegation
            models.CheckConstraint(
                check=~Q(principal=models.F('delegate')),
                name='no_self_delegation',
            ),
        ]
        indexes = [
            models.Index(fields=['farm', 'is_active', 'start_date', 'end_date'],
                         name='delegation_active_range_idx'),
        ]

    def clean(self):
        super().clean()
        if self.principal_id and self.delegate_id and self.principal_id == self.delegate_id:
            raise ValidationError('لا يمكن تفويض الصلاحية لنفس المستخدم.')
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError('تاريخ البداية يجب أن يكون قبل تاريخ الانتهاء.')
        if not self.reason or len(self.reason.strip()) < 10:
            raise ValidationError('سبب التفويض إلزامي (10 أحرف على الأقل).')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @staticmethod
    def get_active_delegations(user, farm_id, role=None):
        """
        Returns active delegations for a user on a specific farm.
        Used by permission checks to include delegated authority.
        """
        from django.utils import timezone
        today = timezone.localdate()
        qs = RoleDelegation.objects.filter(
            delegate=user,
            farm_id=farm_id,
            is_active=True,
            start_date__lte=today,
            end_date__gte=today,
            deleted_at__isnull=True,
        )
        if role:
            qs = qs.filter(role=role)
        return qs

    def __str__(self):
        return (
            f"{self.principal} → {self.delegate} "
            f"({self.role} @ {self.farm}, "
            f"{self.start_date} - {self.end_date})"
        )
