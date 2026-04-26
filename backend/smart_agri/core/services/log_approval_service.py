from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from smart_agri.core.api.permissions import _user_is_farm_manager
from smart_agri.core.models.log import AuditLog, DailyLog, FuelConsumptionAlert
from smart_agri.core.services.variance import compute_log_variance
from smart_agri.core.services.diesel_monitoring import DieselMonitoringService
from smart_agri.finance.models import FiscalPeriod

import logging

logger = logging.getLogger(__name__)


class LogApprovalService:
    @staticmethod
    def _resolve_log(log_or_id):
        if isinstance(log_or_id, DailyLog):
            return DailyLog.objects.select_for_update().get(pk=log_or_id.pk)
        return DailyLog.objects.select_for_update().get(pk=log_or_id)

    @staticmethod
    def _user_is_supervisor_or_above(user):
        """Check if user is supervisor, manager, or above."""
        if not user or not getattr(user, "is_authenticated", False):
            return False
        if user.is_superuser:
            return True
        # Arabic roles matching FarmMembership.ROLE_CHOICES
        SUPERVISOR_ROLES = {
            "مدير النظام", "مدير المزرعة", "مشرف ميداني",
            "رئيس الحسابات", "المدير المالي للمزرعة", "محاسب القطاع",
            "مراجع القطاع", "رئيس حسابات القطاع", "المدير المالي لقطاع المزارع",
            "مدير القطاع", "مدقق مالي",
            "Supervisor", "Field Supervisor",
            "Manager", "Farm Manager", "Finance Manager",
            "Sector Accountant", "Sector Reviewer",
            "Sector Chief Accountant", "Sector Finance Director",
            "Sector Director", "Auditor",
        }
        # Check Django groups
        group_roles = {group.name for group in user.groups.all()}
        if group_roles & SUPERVISOR_ROLES:
            return True
        # Check FarmMembership.role
        from smart_agri.accounts.models import FarmMembership
        return FarmMembership.objects.filter(
            user=user, role__in=SUPERVISOR_ROLES
        ).exists()

    @staticmethod
    def _allows_creator_self_variance_approval(log):
        farm = getattr(log, "farm", None)
        try:
            settings = farm.settings if farm is not None else None
        except ObjectDoesNotExist:
            settings = None
        return bool(getattr(settings, "allow_creator_self_variance_approval", False))

    @staticmethod
    def _record_variance_self_approval_audit(user, log):
        approved_at = getattr(log, "variance_approved_at", None)
        AuditLog.objects.create(
            actor=user,
            farm=getattr(log, "farm", None),
            action="daily_log_variance_self_approved",
            model="DailyLog",
            object_id=str(log.pk),
            new_payload={
                "daily_log_id": log.pk,
                "variance_status": log.variance_status,
                "variance_note": log.variance_note,
                "approved_by_id": user.id,
                "approved_at": approved_at.isoformat() if approved_at else None,
            },
            reason="Creator self-approved critical variance under explicit farm policy.",
        )

    @staticmethod
    def validate_modification_window(log_date, farm, user=None):
        period = FiscalPeriod.objects.select_for_update().filter(
            fiscal_year__farm=farm,
            start_date__lte=log_date,
            end_date__gte=log_date,
        ).first()
        if not period:
            return
        status = FiscalPeriod._normalize_status(period.status)
        if status == FiscalPeriod.STATUS_HARD_CLOSE:
            raise ValidationError(f"تم إغلاق الفترة المالية ({period}) نهائياً (Hard Close). يمنع أي تعديل.")

        # [AGRI-GUARDIAN] Canonical period state is `soft_close`.
        # Legacy values are normalized by FiscalPeriod._normalize_status().
        if status == FiscalPeriod.STATUS_SOFT_CLOSE:
            is_auditor = user and (
                user.has_perm('core.can_audit_finance') or user.is_superuser
            )
            if not is_auditor:
                raise ValidationError(
                    f"الفترة المالية ({period}) في حالة إغلاق مؤقت (Soft Close). التعديل محصور بالمدققين."
                )

    @staticmethod
    @transaction.atomic
    def submit_log(user, log_id: int):
        log = LogApprovalService._resolve_log(log_id)
        LogApprovalService.validate_modification_window(log.log_date, log.farm, user)

        if log.status != DailyLog.STATUS_DRAFT:
            raise ValidationError(f"لا يمكن إرسال السجل من الحالة الحالية: {log.status}.")
        if not log.activities.filter(deleted_at__isnull=True).exists():
            raise ValidationError("لا يمكن إرسال سجل فارغ.")

        diesel_result = DieselMonitoringService.evaluate_log(log)
        log.fuel_alert_status = diesel_result["status"]
        log.fuel_alert_note = diesel_result["note"]
        if diesel_result["status"] == FuelConsumptionAlert.STATUS_CRITICAL:
            raise ValidationError(f"تنبيه استهلاك الديزل: {diesel_result['note']}")

        log.status = DailyLog.STATUS_SUBMITTED
        log.updated_by = user

        # [AGRI-GUARDIAN Axis 8] Proactively compute variance at submit time
        # so frontend can display variance_status and gate the approve button.
        variance = compute_log_variance(log)
        log.variance_status = variance["status"]

        log.save(update_fields=[
            "status", "updated_by", "updated_at",
            "fuel_alert_status", "fuel_alert_note",
            "variance_status",
        ])
        return log

    @staticmethod
    @transaction.atomic
    def note_warning(user, log_id: int, note: str):
        if not note:
            raise ValidationError("ملاحظة الانحراف مطلوبة.")
        if not LogApprovalService._user_is_supervisor_or_above(user):
            raise PermissionDenied("تسجيل ملاحظة انحراف تحذيري يتطلب صلاحية مشرف أو أعلى.")

        log = LogApprovalService._resolve_log(log_id)
        LogApprovalService.validate_modification_window(log.log_date, log.farm, user)

        variance = compute_log_variance(log)
        log.variance_status = variance["status"]
        if log.variance_status != "WARNING":
            raise ValidationError("حالة الانحراف الحالية ليست WARNING.")
        log.variance_note = note
        log.updated_by = user
        log.save(update_fields=["variance_status", "variance_note", "updated_by", "updated_at"])
        return log

    @staticmethod
    @transaction.atomic
    def approve_variance(user, log_id: int, note: str):
        if not note:
            raise ValidationError("ملاحظة الانحراف مطلوبة.")
        if not _user_is_farm_manager(user):
            raise PermissionDenied("اعتماد الانحراف الحرج يتطلب صلاحية مدير.")

        log = LogApprovalService._resolve_log(log_id)
        LogApprovalService.validate_modification_window(log.log_date, log.farm, user)
        creator_self_approval = log.created_by_id == user.id
        if creator_self_approval and not LogApprovalService._allows_creator_self_variance_approval(log):
            raise ValidationError("لا يمكنك اعتماد انحراف سجل قمت بإنشائه.")

        variance = compute_log_variance(log)
        log.variance_status = variance["status"]
        if log.variance_status != "CRITICAL":
            raise ValidationError("اعتماد المدير للانحراف مسموح فقط لحالة CRITICAL.")

        log.variance_note = note
        log.variance_approved_by = user
        log.variance_approved_at = timezone.now()
        log.updated_by = user
        log.save(
            update_fields=[
                "variance_status",
                "variance_note",
                "variance_approved_by",
                "variance_approved_at",
                "updated_by",
                "updated_at",
            ]
        )
        if creator_self_approval:
            LogApprovalService._record_variance_self_approval_audit(user, log)
        return log

    @staticmethod
    @transaction.atomic
    def approve_log(user, log_id: int):
        log = LogApprovalService._resolve_log(log_id)
        LogApprovalService.validate_modification_window(log.log_date, log.farm, user)

        if log.status != DailyLog.STATUS_SUBMITTED:
            raise ValidationError(f"لا يمكن اعتماد السجل من الحالة الحالية: {log.status}.")
        if log.created_by_id == user.id:
            raise ValidationError("مخالفة مبدأ الفصل الرقابي: منشئ السجل لا يمكنه اعتماده.")

        activities = log.activities.filter(deleted_at__isnull=True)
        for act in activities:
            if act.cost_total is None:
                raise ValidationError(f"النشاط {act.pk} لا يحتوي على تكلفة إجمالية معرفة.")
            if act.cost_total == 0 and act.days_spent and act.days_spent > 0:
                raise ValidationError(
                    f"النشاط {act.pk} يحتوي على وحدات عمل ({act.days_spent}) ولكن التكلفة صفر."
                )

        variance = compute_log_variance(log)
        log.variance_status = variance["status"]

        if variance["status"] == "WARNING" and not log.variance_note:
            raise ValidationError(
                "انحراف WARNING يتطلب ملاحظة مشرف قبل الاعتماد. "
                "(WARNING variance requires supervisor note before approval.)"
            )
        if variance["status"] == "CRITICAL":
            if not log.variance_approved_by:
                raise ValidationError(
                    "انحراف CRITICAL يتطلب اعتماد مدير قبل الترحيل. "
                    "(CRITICAL variance requires manager approval before posting.)"
                )
            if not _user_is_farm_manager(log.variance_approved_by):
                raise ValidationError("اعتماد انحراف CRITICAL يجب أن يتم بواسطة مدير.")
            if not log.variance_approved_at:
                raise ValidationError("توقيت اعتماد انحراف CRITICAL مطلوب.")

        from smart_agri.finance.models import FinancialLedger

        ledger_count = FinancialLedger.objects.filter(activity__log=log).count()
        if ledger_count == 0:
            logger.warning("Log %s approved with no linked ledger entries.", log.id)

        log.status = DailyLog.STATUS_APPROVED
        log.approved_by = user
        log.approved_at = timezone.now()
        log.save(
            update_fields=[
                "variance_status",
                "status",
                "approved_by",
                "approved_at",
                "updated_at",
            ]
        )

        # [Phase 10] Link DailyLog.status to Timesheet approval
        from smart_agri.core.models.hr import Timesheet
        Timesheet.objects.filter(activity__log=log).update(
            is_approved=True,
            approved_by=user,
        )

        return log

    @staticmethod
    @transaction.atomic
    def reject_log(user, log_id: int, reason: str):
        if not reason:
            raise ValidationError("سبب الرفض مطلوب.")

        log = LogApprovalService._resolve_log(log_id)
        LogApprovalService.validate_modification_window(log.log_date, log.farm, user)

        if log.status != DailyLog.STATUS_SUBMITTED:
            raise ValidationError(f"لا يمكن رفض السجل من الحالة الحالية: {log.status}.")

        log.status = DailyLog.STATUS_REJECTED
        log.rejection_reason = reason
        log.updated_by = user
        log.save(update_fields=["status", "rejection_reason", "updated_by", "updated_at"])
        return log

    @staticmethod
    @transaction.atomic
    def reopen_log(user, log_id: int):
        log = LogApprovalService._resolve_log(log_id)
        LogApprovalService.validate_modification_window(log.log_date, log.farm, user)

        if log.status != DailyLog.STATUS_REJECTED:
            raise ValidationError(f"لا يمكن إعادة فتح السجل إلا إذا كان مرفوضاً. الحالة الحالية: {log.status}")
        
        if log.created_by_id != user.id and not LogApprovalService._user_is_supervisor_or_above(user):
            raise PermissionDenied("إعادة فتح السجل مسموح فقط لمنشئ السجل أو المشرفين.")

        # [AGRI-GUARDIAN FIX] Track correction history
        # Store correction count in metadata for audit trail
        correction_count = getattr(log, '_correction_count', 0)
        if hasattr(log, 'metadata') and isinstance(log.metadata, dict):
            correction_count = log.metadata.get('correction_count', 0) + 1
            log.metadata['correction_count'] = correction_count
            log.metadata.setdefault('correction_history', []).append({
                'reopened_at': timezone.now().isoformat(),
                'reopened_by': user.id,
                'previous_rejection_reason': log.rejection_reason,
            })
        elif hasattr(log, 'notes'):
            # Fallback: append correction marker to notes
            marker = f"\n[تعديل #{correction_count + 1}]"
            if marker not in (log.notes or ''):
                log.notes = (log.notes or '') + marker

        log.status = DailyLog.STATUS_DRAFT
        log.rejection_reason = ""
        log.variance_status = ""
        log.variance_note = ""
        log.variance_approved_by = None
        log.variance_approved_at = None
        log.updated_by = user

        update_fields = [
            "status", 
            "rejection_reason", 
            "variance_status", 
            "variance_note", 
            "variance_approved_by", 
            "variance_approved_at", 
            "updated_by", 
            "updated_at"
        ]
        if hasattr(log, 'metadata'):
            update_fields.append('metadata')
        if hasattr(log, 'notes'):
            update_fields.append('notes')

        log.save(update_fields=update_fields)

        # [Phase 10] Link DailyLog.status to Timesheet approval (Unlock)
        from smart_agri.core.models.hr import Timesheet
        Timesheet.objects.filter(activity__log=log).update(
            is_approved=False,
            approved_by=None,
        )

        return log
