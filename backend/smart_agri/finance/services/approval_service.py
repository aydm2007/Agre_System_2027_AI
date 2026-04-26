from collections import Counter, defaultdict
from decimal import Decimal
from datetime import timedelta
import logging

from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.db.models import F, Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from smart_agri.core.api.permissions import (
    _ensure_user_has_farm_access,
    user_has_farm_role,
    user_has_sector_finance_authority,
    user_has_any_farm_role,
)
from smart_agri.finance.models import ApprovalRequest, ApprovalRule, ApprovalStageEvent
from smart_agri.core.models import IntegrationOutboxEvent
from smart_agri.core.models.log import Attachment
from smart_agri.core.models.policy_engine import PolicyActivationRequest, PolicyExceptionRequest
from smart_agri.core.models.settings import FarmSettings, RemoteReviewLog
from smart_agri.core.services.attachment_policy_service import AttachmentPolicyService
from smart_agri.core.services.ops_health_service import OpsHealthService
from smart_agri.core.services.policy_engine_service import PolicyEngineService
from smart_agri.core.services.remote_review_service import RemoteReviewService
from smart_agri.finance.services.approval_state_transitions import (
    append_history,
    finalize_request,
    record_stage_event,
    reject_request_state,
    reopen_request_state,
    stage_events_payload as build_stage_events_payload,
)

logger = logging.getLogger(__name__)


class ApprovalGovernanceService:
    """Canonical service layer for approval rules and approval requests."""

    STAGE_SLA_HOURS = {
        ApprovalRule.ROLE_MANAGER: 24,
        ApprovalRule.ROLE_FARM_FINANCE_MANAGER: 24,
        ApprovalRule.ROLE_SECTOR_ACCOUNTANT: 24,
        ApprovalRule.ROLE_SECTOR_REVIEWER: 36,
        ApprovalRule.ROLE_CHIEF_ACCOUNTANT: 48,
        ApprovalRule.ROLE_FINANCE_DIRECTOR: 72,
        ApprovalRule.ROLE_SECTOR_DIRECTOR: 96,
    }

    ATTENTION_SEVERITY_ORDER = {
        "critical": 0,
        "high": 1,
        "medium": 2,
        "low": 3,
        "none": 4,
    }

    @staticmethod
    def _require_sector_finance_authority(user):
        if getattr(user, "is_superuser", False):
            return
        if user.has_perm("finance.can_sector_finance_approve") or user_has_sector_finance_authority(user):
            return
        raise PermissionDenied("ليس لديك صلاحية إنشاء/تعديل قواعد الموافقات (يتطلب صلاحية مالية قطاعية).")

    ROLE_LABELS = {
        ApprovalRule.ROLE_MANAGER: 'مدير المزرعة',
        ApprovalRule.ROLE_FARM_FINANCE_MANAGER: 'المدير المالي للمزرعة',
        ApprovalRule.ROLE_SECTOR_ACCOUNTANT: 'محاسب القطاع',
        ApprovalRule.ROLE_SECTOR_REVIEWER: 'مراجع القطاع',
        ApprovalRule.ROLE_CHIEF_ACCOUNTANT: 'رئيس حسابات القطاع',
        ApprovalRule.ROLE_FINANCE_DIRECTOR: 'المدير المالي لقطاع المزارع',
        ApprovalRule.ROLE_SECTOR_DIRECTOR: 'مدير القطاع',
    }

    ROLE_LADDER = [
        ApprovalRule.ROLE_FARM_FINANCE_MANAGER,
        ApprovalRule.ROLE_SECTOR_ACCOUNTANT,
        ApprovalRule.ROLE_SECTOR_REVIEWER,
        ApprovalRule.ROLE_CHIEF_ACCOUNTANT,
        ApprovalRule.ROLE_FINANCE_DIRECTOR,
        ApprovalRule.ROLE_SECTOR_DIRECTOR,
    ]

    WORKFLOW_BLUEPRINTS = {
        (ApprovalRule.MODULE_FINANCE, 'supplier_settlement'): {
            'label': 'Supplier Settlement',
            'requires_sector_final_in_strict_finance': True,
            'supports_reopen': True,
            'supports_override': True,
            'requires_attachment_scan_pass': True,
        },
        (ApprovalRule.MODULE_FINANCE, 'petty_cash_disbursement'): {
            'label': 'Petty Cash Disbursement',
            'requires_sector_final_in_strict_finance': True,
            'supports_reopen': True,
            'supports_override': True,
            'requires_attachment_scan_pass': True,
        },
        (ApprovalRule.MODULE_FINANCE, 'petty_cash_settlement'): {
            'label': 'Petty Cash Settlement',
            'requires_sector_final_in_strict_finance': True,
            'supports_reopen': True,
            'supports_override': True,
            'requires_attachment_scan_pass': True,
        },
        (ApprovalRule.MODULE_FINANCE, 'fixed_asset_posting'): {
            'label': 'Fixed Asset Posting',
            'requires_sector_final_in_strict_finance': True,
            'supports_reopen': True,
            'supports_override': True,
            'requires_attachment_scan_pass': True,
        },
        (ApprovalRule.MODULE_FINANCE, 'fuel_reconciliation'): {
            'label': 'Fuel Reconciliation',
            'requires_sector_final_in_strict_finance': True,
            'supports_reopen': True,
            'supports_override': True,
            'requires_attachment_scan_pass': True,
        },
        (ApprovalRule.MODULE_FINANCE, 'contract_payment_posting'): {
            'label': 'Contract Payment Posting',
            'requires_sector_final_in_strict_finance': True,
            'supports_reopen': True,
            'supports_override': True,
            'requires_attachment_scan_pass': True,
        },
    }

    @classmethod
    def _workflow_blueprint(cls, *, module: str | None, action_name: str | None) -> dict:
        base = {
            'label': action_name or 'generic_approval',
            'requires_sector_final_in_strict_finance': False,
            'supports_reopen': True,
            'supports_override': True,
            'requires_attachment_scan_pass': False,
        }
        specific = cls.WORKFLOW_BLUEPRINTS.get((module, action_name), {})
        return {**base, **specific}

    @classmethod
    def _user_has_exact_stage_role(cls, *, user, req: ApprovalRequest) -> bool:
        role = req.required_role
        if role == ApprovalRule.ROLE_MANAGER:
            return user_has_any_farm_role(user, {"مدير المزرعة", "مدير النظام"})
        if role == ApprovalRule.ROLE_FARM_FINANCE_MANAGER:
            return user_has_any_farm_role(user, {"المدير المالي للمزرعة", "مدير النظام"})
        if role == ApprovalRule.ROLE_SECTOR_ACCOUNTANT:
            return user_has_any_farm_role(user, {"محاسب القطاع", "مدير النظام"})
        if role == ApprovalRule.ROLE_SECTOR_REVIEWER:
            return user_has_any_farm_role(user, {"مراجع القطاع", "مدير النظام"})
        if role == ApprovalRule.ROLE_CHIEF_ACCOUNTANT:
            return user_has_any_farm_role(user, {"رئيس حسابات القطاع", "مدير النظام"})
        if role == ApprovalRule.ROLE_FINANCE_DIRECTOR:
            return user_has_any_farm_role(user, {"المدير المالي لقطاع المزارع", "مدير النظام"}) or user_has_sector_finance_authority(user)
        if role == ApprovalRule.ROLE_SECTOR_DIRECTOR:
            return user_has_any_farm_role(user, {"مدير القطاع", "مدير النظام"})
        return False

    @classmethod
    def can_override_stage(cls, user, req: ApprovalRequest) -> bool:
        if getattr(user, "is_superuser", False):
            return True
        if req.status != ApprovalRequest.STATUS_PENDING:
            return False
        if req.required_role == ApprovalRule.ROLE_SECTOR_DIRECTOR:
            return False
        override_roles = {"المدير المالي لقطاع المزارع", "مدير القطاع", "مدير النظام"}
        return user_has_any_farm_role(user, override_roles) or user_has_sector_finance_authority(user)

    @staticmethod
    def _settings_for_farm(farm):
        settings_obj = getattr(farm, "settings", None)
        return PolicyEngineService.runtime_settings_for_farm(farm=farm, settings_obj=settings_obj)

    @classmethod
    def _build_role_chain(cls, final_role: str, *, farm=None, module: str | None = None) -> list[str]:
        if final_role == ApprovalRule.ROLE_MANAGER:
            return [ApprovalRule.ROLE_MANAGER]
        if final_role not in cls.ROLE_LADDER:
            return [final_role]
        idx = cls.ROLE_LADDER.index(final_role)
        chain = cls.ROLE_LADDER[: idx + 1]
        if farm is None:
            return chain
        settings_obj = cls._settings_for_farm(farm)
        approval_profile = getattr(settings_obj, 'approval_profile', FarmSettings.APPROVAL_PROFILE_TIERED)
        if approval_profile == FarmSettings.APPROVAL_PROFILE_BASIC:
            if final_role in {ApprovalRule.ROLE_MANAGER, ApprovalRule.ROLE_FARM_FINANCE_MANAGER}:
                return [ApprovalRule.ROLE_FARM_FINANCE_MANAGER]
            return [ApprovalRule.ROLE_FARM_FINANCE_MANAGER, final_role]
        if approval_profile == FarmSettings.APPROVAL_PROFILE_STRICT_FINANCE and module == ApprovalRule.MODULE_FINANCE:
            return chain
        return chain

    @classmethod
    def _next_stage_role(cls, *, final_role: str, current_stage: int, farm=None, module: str | None = None) -> str | None:
        chain = cls._build_role_chain(final_role, farm=farm, module=module)
        if current_stage >= len(chain):
            return None
        return chain[current_stage]

    @classmethod
    def _current_stage_started_at(cls, req: ApprovalRequest):
        history = list(req.approval_history or [])
        if history:
            return timezone.datetime.fromisoformat(history[-1]['at']) if history[-1].get('at') else req.updated_at or req.created_at
        return req.updated_at or req.created_at

    @classmethod
    def _sla_hours_for_role(cls, *, role: str, farm) -> int:
        settings = getattr(farm, 'settings', None)
        base = cls.STAGE_SLA_HOURS.get(role, 24)
        if getattr(settings, 'remote_site', False):
            return base + 12
        return base

    @classmethod
    def workflow_blueprint_for_request(cls, *, req: ApprovalRequest) -> dict:
        settings_obj = cls._settings_for_farm(req.farm)
        chain = cls._build_role_chain(req.final_required_role, farm=req.farm, module=req.module)
        blockers = cls._request_blockers(req=req, settings_obj=settings_obj)
        return {
            **cls._workflow_blueprint(module=req.module, action_name=req.action),
            'module': req.module,
            'action': req.action,
            'approval_profile': getattr(settings_obj, 'approval_profile', FarmSettings.APPROVAL_PROFILE_TIERED),
            'farm_tier': (getattr(req.farm, 'tier', None) or 'SMALL').upper(),
            'supports_reopen': req.status == ApprovalRequest.STATUS_REJECTED,
            'supports_override': req.status == ApprovalRequest.STATUS_PENDING,
            'policy_context': cls._approval_policy_context(req=req, settings_obj=settings_obj),
            'blockers': blockers['blockers'],
            'remote_review_blocked': blockers['remote_review_blocked'],
            'attachment_scan_blocked': blockers['attachment_scan_blocked'],
            'strict_finance_required': blockers['strict_finance_required'],
            'stage_chain': [
                {'stage': idx + 1, 'role': role, 'label': cls.ROLE_LABELS.get(role, role)}
                for idx, role in enumerate(chain)
            ],
        }

    @classmethod
    def queue_snapshot(cls, *, req: ApprovalRequest) -> dict:
        started_at = cls._current_stage_started_at(req)
        sla_hours = cls._sla_hours_for_role(role=req.required_role, farm=req.farm)
        due_at = started_at + timedelta(hours=sla_hours)
        now = timezone.now()
        chain = cls._build_role_chain(req.final_required_role, farm=req.farm, module=req.module)
        settings_obj = cls._settings_for_farm(req.farm)
        blockers = cls._request_blockers(req=req, settings_obj=settings_obj)
        lane_health, attention_severity, attention_bucket = cls._queue_health(
            blockers=blockers,
            is_overdue=now > due_at,
        )
        return {
            'request_id': req.id,
            'farm_id': req.farm_id,
            'current_role': req.required_role,
            'current_role_label': cls.ROLE_LABELS.get(req.required_role, req.required_role),
            'current_stage': req.current_stage,
            'total_stages': req.total_stages,
            'stage_progress_pct': round((req.current_stage / max(req.total_stages, 1)) * 100, 2),  # agri-guardian: decimal-safe non-financial progress metric
            'stage_chain': [
                {'role': role, 'label': cls.ROLE_LABELS.get(role, role), 'stage': idx + 1}
                for idx, role in enumerate(chain)
            ],
            'started_at': started_at.isoformat() if started_at else None,
            'due_at': due_at.isoformat(),
            'is_overdue': now > due_at,
            'lane_sla_hours': sla_hours,
            'status': req.status,
            'policy_context': cls._approval_policy_context(req=req, settings_obj=settings_obj),
            'strict_finance_required': blockers['strict_finance_required'],
            'remote_review_blocked': blockers['remote_review_blocked'],
            'attachment_scan_blocked': blockers['attachment_scan_blocked'],
            'blockers': blockers['blockers'],
            'lane_health': lane_health,
            'attention_severity': attention_severity,
            'attention_bucket': attention_bucket,
        }

    @classmethod
    def _approval_policy_context(cls, *, req: ApprovalRequest, settings_obj) -> dict:
        from smart_agri.finance.services.tier_policy import TierPolicy
        amount = req.requested_amount or Decimal("0.0000")
        thresholds = TierPolicy.resolve_thresholds(farm=req.farm, settings_obj=settings_obj)
        local_threshold = thresholds["local_finance_threshold"]
        sector_review_threshold = thresholds["sector_review_threshold"]
        committee_threshold = thresholds["procurement_committee_threshold"]
        strict_finance_required = bool(
            req.module == ApprovalRule.MODULE_FINANCE
            and getattr(settings_obj, "approval_profile", FarmSettings.APPROVAL_PROFILE_TIERED)
            == FarmSettings.APPROVAL_PROFILE_STRICT_FINANCE
        )
        if amount <= local_threshold:
            threshold_reason = "within_local_finance_threshold"
        elif amount <= sector_review_threshold:
            threshold_reason = "requires_sector_accountant_review"
        elif amount <= committee_threshold:
            threshold_reason = "requires_sector_reviewer_review"
        else:
            threshold_reason = "requires_escalated_sector_chain"
        return {
            "approval_profile": getattr(settings_obj, "approval_profile", FarmSettings.APPROVAL_PROFILE_TIERED),
            "approval_profile_source": getattr(settings_obj, "_effective_policy_source", "farm_settings"),
            "threshold_reason": threshold_reason,
            "local_finance_threshold": str(local_threshold),
            "sector_review_threshold": str(sector_review_threshold),
            "procurement_committee_threshold": str(committee_threshold),
            "effective_mode": getattr(settings_obj, "mode", FarmSettings.MODE_SIMPLE),
            "strict_finance_required": strict_finance_required,
        }

    @staticmethod
    def _request_attachments(req: ApprovalRequest) -> list[Attachment]:
        target = req.transaction_source
        if target is None:
            return []
        if isinstance(target, Attachment):
            return [target]
        if hasattr(target, "attachment") and getattr(target, "attachment", None):
            return [getattr(target, "attachment")]
        if hasattr(target, "attachments"):
            related = getattr(target, "attachments")
            if hasattr(related, "all"):
                return list(related.all())
        return []

    @classmethod
    def _request_blockers(cls, *, req: ApprovalRequest, settings_obj=None) -> dict:
        settings_obj = settings_obj or cls._settings_for_farm(req.farm)
        workflow = cls._workflow_blueprint(module=req.module, action_name=req.action)
        policy_context = cls._approval_policy_context(req=req, settings_obj=settings_obj)
        attachments = cls._request_attachments(req)
        remote_review_blocked = bool(
            req.module == ApprovalRule.MODULE_FINANCE
            and getattr(settings_obj, "remote_site", False)
            and getattr(settings_obj, "weekly_remote_review_required", False)
            and RemoteReviewService.is_overdue(settings_obj)
        )
        attachment_scan_blocked = False
        attachment_block_reason = ""
        if workflow.get("requires_attachment_scan_pass"):
            mandatory_attachment = bool(getattr(settings_obj, "mandatory_attachment_for_cash", True))
            if mandatory_attachment and not attachments:
                attachment_scan_blocked = True
                attachment_block_reason = "missing_required_attachment"
            else:
                statuses = {getattr(att, "malware_scan_status", "") for att in attachments}
                if Attachment.MALWARE_SCAN_QUARANTINED in statuses:
                    attachment_scan_blocked = True
                    attachment_block_reason = "attachment_scan_blocked"
                elif (
                    getattr(settings_obj, "attachment_require_clean_scan_for_strict", False)
                    and Attachment.MALWARE_SCAN_PENDING in statuses
                ):
                    attachment_scan_blocked = True
                    attachment_block_reason = "attachment_scan_pending"
        strict_finance_required = bool(policy_context.get("strict_finance_required"))
        blockers = []
        if remote_review_blocked:
            blockers.append("remote_review_blocked")
        if attachment_scan_blocked:
            blockers.append(attachment_block_reason or "attachment_scan_blocked")
        if strict_finance_required and req.required_role in {
            ApprovalRule.ROLE_FINANCE_DIRECTOR,
            ApprovalRule.ROLE_SECTOR_DIRECTOR,
        }:
            blockers.append("strict_finance_final_required")
        return {
            "strict_finance_required": strict_finance_required,
            "remote_review_blocked": remote_review_blocked,
            "attachment_scan_blocked": attachment_scan_blocked,
            "attachment_block_reason": attachment_block_reason,
            "blockers": blockers,
        }

    @classmethod
    def _queue_health(cls, *, blockers: dict, is_overdue: bool, director_attention: bool = False, farm_finance_attention: bool = False) -> tuple[str, str, str]:
        if blockers.get("remote_review_blocked") or blockers.get("attachment_scan_blocked"):
            return "blocked", "critical", "blocked_by_policy"
        if director_attention:
            return "attention", "high", "sector_final_attention"
        if is_overdue:
            return "attention", "high", "approval_overdue"
        if farm_finance_attention:
            return "attention", "medium", "farm_finance_volume_attention"
        return "healthy", "none", ""

    @classmethod
    def pending_for_role(cls, role: str):
        return ApprovalRequest.objects.filter(
            deleted_at__isnull=True,
            status=ApprovalRequest.STATUS_PENDING,
            required_role=role,
        ).select_related('farm')

    @classmethod
    def overdue_queryset(cls):
        overdue_ids = []
        for req in ApprovalRequest.objects.filter(deleted_at__isnull=True, status=ApprovalRequest.STATUS_PENDING).select_related('farm'):
            if cls.queue_snapshot(req=req)['is_overdue']:
                overdue_ids.append(req.id)
        return ApprovalRequest.objects.filter(id__in=overdue_ids)

    @classmethod
    def work_queue_for_user(cls, user):
        rows = []
        for req in ApprovalRequest.objects.filter(deleted_at__isnull=True, status=ApprovalRequest.STATUS_PENDING).select_related('farm'):
            if cls.can_approve(user, req):
                rows.append(cls.queue_snapshot(req=req))
        return rows

    @classmethod
    def queue_summary_for_user(cls, user):
        rows = cls.work_queue_for_user(user)
        lanes = []
        blocked_count = sum(1 for row in rows if row.get('lane_health') == 'blocked')
        attention_count = sum(1 for row in rows if row.get('lane_health') == 'attention')
        for role in cls.ROLE_LADDER:
            items = [r for r in rows if r['current_role'] == role]
            overdue = sum(1 for r in items if r['is_overdue'])
            if items:
                lanes.append({
                    'role': role,
                    'label': cls.ROLE_LABELS.get(role, role),
                    'count': len(items),
                    'overdue': overdue,
                    'blocked': sum(1 for r in items if r.get('lane_health') == 'blocked'),
                    'attention': sum(1 for r in items if r.get('lane_health') == 'attention'),
                })
        return {
            'pending_count': len(rows),
            'overdue_count': sum(1 for r in rows if r['is_overdue']),
            'blocked_count': blocked_count,
            'attention_count': attention_count,
            'lane_health_counts': {
                'blocked': blocked_count,
                'attention': attention_count,
                'healthy': sum(1 for row in rows if row.get('lane_health') == 'healthy'),
            },
            'lanes': lanes,
        }

    @classmethod
    def maintenance_summary(cls) -> dict:
        pending_qs = ApprovalRequest.objects.filter(
            deleted_at__isnull=True,
            status=ApprovalRequest.STATUS_PENDING,
        ).select_related('farm')
        pending_rows = list(pending_qs)
        overdue = 0
        strict_finance = 0
        remote_review_blocked_requests = 0
        attachment_scan_blocked_requests = 0
        for req in pending_rows:
            snapshot = cls.queue_snapshot(req=req)
            if snapshot['is_overdue']:
                overdue += 1
            settings_obj = cls._settings_for_farm(req.farm)
            if getattr(settings_obj, 'approval_profile', FarmSettings.APPROVAL_PROFILE_TIERED) == FarmSettings.APPROVAL_PROFILE_STRICT_FINANCE:
                strict_finance += 1
            if snapshot.get('remote_review_blocked'):
                remote_review_blocked_requests += 1
            if snapshot.get('attachment_scan_blocked'):
                attachment_scan_blocked_requests += 1
        remote_snapshot = RemoteReviewService.governance_snapshot()
        attachment_runtime = AttachmentPolicyService.security_runtime_summary()
        remote_due_reviews = remote_snapshot.get('due_count', 0)
        return {
            'pending_requests': len(pending_rows),
            'overdue_requests': overdue,
            'strict_finance_pending': strict_finance,
            'remote_review_blocked_requests': remote_review_blocked_requests,
            'attachment_scan_blocked_requests': attachment_scan_blocked_requests,
            'remote_farms_due_review': remote_due_reviews,
            'remote_review_escalations': remote_snapshot.get('open_escalations', 0),
            'remote_review_blocked_escalations': remote_snapshot.get('blocked_escalations', 0),
            'generated_at': timezone.now().isoformat(),
            'attachment_runtime': attachment_runtime,
            'role_workbench_rows': len(cls.role_workbench_snapshot().get('rows', [])),
        }

    @classmethod
    def runtime_governance_snapshot(cls) -> dict:
        maintenance = cls.maintenance_summary()
        workbench = cls.role_workbench_snapshot()
        attention = cls.attention_feed()
        blocked_buckets = Counter()
        for item in attention.get('items', []):
            kind = item.get('kind')
            if kind == 'approval_overdue':
                blocked_buckets['overdue'] += 1
            elif kind == 'remote_review_blocked':
                blocked_buckets['remote_review_blocked'] += 1
            elif kind == 'attachment_runtime_block':
                blocked_buckets['attachment_scan_blocked'] += 1
            elif kind == 'sector_final_attention':
                blocked_buckets['sector_final_attention'] += 1
            elif kind == 'farm_finance_volume_attention':
                blocked_buckets['strict_finance_final_required'] += 1
        rows = list(workbench.get('rows', []))
        lane_health_totals = {
            'healthy': sum(1 for row in rows if row.get('lane_health') == 'healthy'),
            'attention': sum(1 for row in rows if row.get('lane_health') == 'attention'),
            'blocked': sum(1 for row in rows if row.get('lane_health') == 'blocked'),
        }
        snapshot = {
            'generated_at': timezone.now().isoformat(),
            'severity': 'critical' if maintenance.get('attachment_scan_blocked_requests') or maintenance.get('remote_review_blocked_requests') else ('attention' if maintenance.get('overdue_requests') else 'healthy'),
            'pending_requests': maintenance.get('pending_requests', 0),
            'overdue_requests': maintenance.get('overdue_requests', 0),
            'blocked_requests': maintenance.get('remote_review_blocked_requests', 0) + maintenance.get('attachment_scan_blocked_requests', 0),
            'strict_finance_pending': maintenance.get('strict_finance_pending', 0),
            'remote_review_posture': {
                'blocked_requests': maintenance.get('remote_review_blocked_requests', 0),
                'due_farms': maintenance.get('remote_farms_due_review', 0),
                'open_escalations': maintenance.get('remote_review_escalations', 0),
                'blocked_escalations': maintenance.get('remote_review_blocked_escalations', 0),
            },
            'attachment_runtime_posture': {
                'pending_scan': maintenance.get('attachment_runtime', {}).get('pending_scan', 0),
                'quarantined': maintenance.get('attachment_runtime', {}).get('quarantined', 0),
                'due_archive': maintenance.get('attachment_runtime', {}).get('due_archive', 0),
                'scan_mode': maintenance.get('attachment_runtime', {}).get('scan_mode'),
            },
            'lane_health_totals': lane_health_totals,
            'blocked_reasons': dict(blocked_buckets),
            'workbench_rows': rows[:10],
            'request_headers': {
                'request_id': 'X-Request-Id',
                'correlation_id': 'X-Correlation-Id',
            },
        }
        logger.info(
            'approval.runtime.snapshot',
            extra={
                'pending_requests': snapshot['pending_requests'],
                'overdue_requests': snapshot['overdue_requests'],
                'blocked_requests': snapshot['blocked_requests'],
                'strict_finance_pending': snapshot['strict_finance_pending'],
            },
        )
        return snapshot

    @classmethod
    def runtime_governance_detail_snapshot(cls, *, limit: int = 50) -> dict:
        pending_qs = ApprovalRequest.objects.filter(
            deleted_at__isnull=True,
            status=ApprovalRequest.STATUS_PENDING,
        ).select_related("farm", "requested_by")
        rows = []
        for req in pending_qs:
            snapshot = cls.queue_snapshot(req=req)
            if snapshot.get("lane_health") == "healthy":
                continue
            rows.append({
                "request_id": req.id,
                "farm_id": req.farm_id,
                "farm_name": getattr(req.farm, "name", ""),
                "module": req.module,
                "action": req.action,
                "requested_amount": str(req.requested_amount or Decimal("0.0000")),
                "required_role": req.required_role,
                "required_role_label": cls.ROLE_LABELS.get(req.required_role, req.required_role),
                "status": req.status,
                "started_at": snapshot.get("started_at"),
                "due_at": snapshot.get("due_at"),
                "is_overdue": snapshot.get("is_overdue"),
                "lane_health": snapshot.get("lane_health"),
                "attention_bucket": snapshot.get("attention_bucket"),
                "attention_severity": snapshot.get("attention_severity"),
                "blockers": snapshot.get("blockers", []),
                "policy_context": snapshot.get("policy_context", {}),
                "workflow_blueprint": cls.workflow_blueprint_for_request(req=req),
                "requester_name": getattr(req.requested_by, "username", ""),
            })
        rows.sort(
            key=lambda row: (
                0 if row.get("lane_health") == "blocked" else 1,
                0 if row.get("is_overdue") else 1,
                row.get("due_at") or "",
                row.get("farm_name") or "",
            )
        )
        return {
            **cls.runtime_governance_snapshot(),
            "detail_rows": rows[: max(1, int(limit or 50))],
            "filtered_total": len(rows),
        }

    @classmethod
    def role_workbench_snapshot(cls):
        buckets = []
        pending = ApprovalRequest.objects.filter(
            deleted_at__isnull=True,
            status=ApprovalRequest.STATUS_PENDING,
        ).select_related('farm', 'farm__settings')
        grouped = {}
        now = timezone.now()
        settings_cache: dict[int, FarmSettings] = {}
        remote_review_cache: dict[int, bool] = {}
        policy_context_cache: dict[tuple[int, str | None, str | None, str], dict] = {}
        for req in pending:
            key = (req.required_role, req.farm_id)
            settings_obj = settings_cache.get(req.farm_id)
            if settings_obj is None:
                settings_obj = cls._settings_for_farm(req.farm)
                settings_cache[req.farm_id] = settings_obj

            policy_key = (
                req.farm_id,
                req.module,
                req.action,
                str(req.requested_amount or Decimal("0.0000")),
            )
            policy_context = policy_context_cache.get(policy_key)
            if policy_context is None:
                policy_context = cls._approval_policy_context(req=req, settings_obj=settings_obj)
                policy_context_cache[policy_key] = policy_context

            workflow = cls._workflow_blueprint(module=req.module, action_name=req.action)
            if req.farm_id not in remote_review_cache:
                remote_review_cache[req.farm_id] = bool(
                    getattr(settings_obj, "remote_site", False)
                    and getattr(settings_obj, "weekly_remote_review_required", False)
                    and RemoteReviewService.is_overdue(settings_obj)
                )
            remote_review_blocked = bool(
                req.module == ApprovalRule.MODULE_FINANCE and remote_review_cache[req.farm_id]
            )
            attachment_scan_blocked = False
            attachment_block_reason = ""
            attachments: list[Attachment] = []
            if workflow.get("requires_attachment_scan_pass"):
                attachments = cls._request_attachments(req)
                mandatory_attachment = bool(getattr(settings_obj, "mandatory_attachment_for_cash", True))
                if mandatory_attachment and not attachments:
                    attachment_scan_blocked = True
                    attachment_block_reason = "missing_required_attachment"
                else:
                    statuses = {getattr(att, "malware_scan_status", "") for att in attachments}
                    if Attachment.MALWARE_SCAN_QUARANTINED in statuses:
                        attachment_scan_blocked = True
                        attachment_block_reason = "attachment_scan_blocked"
                    elif (
                        getattr(settings_obj, "attachment_require_clean_scan_for_strict", False)
                        and Attachment.MALWARE_SCAN_PENDING in statuses
                    ):
                        attachment_scan_blocked = True
                        attachment_block_reason = "attachment_scan_pending"
            strict_finance_required = bool(policy_context.get("strict_finance_required"))
            blockers = []
            if remote_review_blocked:
                blockers.append("remote_review_blocked")
            if attachment_scan_blocked:
                blockers.append(attachment_block_reason or "attachment_scan_blocked")
            if strict_finance_required and req.required_role in {
                ApprovalRule.ROLE_FINANCE_DIRECTOR,
                ApprovalRule.ROLE_SECTOR_DIRECTOR,
            }:
                blockers.append("strict_finance_final_required")
            started_at = cls._current_stage_started_at(req)
            sla_hours = cls._sla_hours_for_role(role=req.required_role, farm=req.farm)
            due_at = started_at + timedelta(hours=sla_hours)
            is_overdue = now > due_at
            lane_health, attention_severity, attention_bucket = cls._queue_health(
                blockers={
                    "remote_review_blocked": remote_review_blocked,
                    "attachment_scan_blocked": attachment_scan_blocked,
                },
                is_overdue=is_overdue,
            )
            snapshot = {
                "started_at": started_at.isoformat() if started_at else None,
                "policy_context": policy_context,
                "strict_finance_required": strict_finance_required,
                "remote_review_blocked": remote_review_blocked,
                "attachment_scan_blocked": attachment_scan_blocked,
                "blockers": blockers,
                "is_overdue": is_overdue,
                "lane_health": lane_health,
                "attention_severity": attention_severity,
                "attention_bucket": attention_bucket,
            }
            bucket = grouped.setdefault(key, {
                'role': req.required_role,
                'role_label': cls.ROLE_LABELS.get(req.required_role, req.required_role),
                'farm_id': req.farm_id,
                'farm_name': getattr(req.farm, 'name', ''),
                'count': 0,
                'overdue': 0,
                'oldest_started_at': snapshot.get('started_at'),
                'max_stage': req.total_stages,
                'sample_request_ids': [],
                'strict_finance_required': False,
                'remote_review_blocked': False,
                'attachment_scan_blocked': False,
                'blocked_count': 0,
                'policy_context_summary': snapshot.get('policy_context', {}),
                'threshold_reason': snapshot.get('policy_context', {}).get('threshold_reason', ''),
            })
            bucket['count'] += 1
            if snapshot.get('is_overdue'):
                bucket['overdue'] += 1
            if snapshot.get('remote_review_blocked') or snapshot.get('attachment_scan_blocked'):
                bucket['blocked_count'] += 1
            bucket['strict_finance_required'] = bool(bucket['strict_finance_required'] or snapshot.get('strict_finance_required'))
            bucket['remote_review_blocked'] = bool(bucket['remote_review_blocked'] or snapshot.get('remote_review_blocked'))
            bucket['attachment_scan_blocked'] = bool(bucket['attachment_scan_blocked'] or snapshot.get('attachment_scan_blocked'))
            if not bucket.get('threshold_reason') and snapshot.get('policy_context', {}).get('threshold_reason'):
                bucket['threshold_reason'] = snapshot['policy_context']['threshold_reason']
            if len(bucket['sample_request_ids']) < 5:
                bucket['sample_request_ids'].append(req.id)
            started_at = cls._current_stage_started_at(req)
            if started_at is not None:
                bucket_started = bucket.get('_started_obj')
                if bucket_started is None or started_at < bucket_started:
                    bucket['_started_obj'] = started_at
                    bucket['oldest_started_at'] = started_at.isoformat()
        for bucket in grouped.values():
            started_obj = bucket.pop('_started_obj', None)
            bucket['oldest_age_hours'] = round(((now - started_obj).total_seconds() / 3600), 2) if started_obj else 0  # agri-guardian: decimal-safe non-financial elapsed hours
            buckets.append(bucket)
        for bucket in buckets:
            role = bucket.get('role')
            bucket['owner_scope'] = 'farm' if role == ApprovalRule.ROLE_FARM_FINANCE_MANAGER else 'sector'
            bucket['director_attention'] = bool(bucket.get('overdue')) or role == ApprovalRule.ROLE_SECTOR_DIRECTOR
            bucket['farm_finance_attention'] = role == ApprovalRule.ROLE_FARM_FINANCE_MANAGER and (bucket.get('overdue') > 0 or bucket.get('count', 0) >= 3)
            bucket['attention_reason'] = 'sector_final_or_overdue' if bucket['director_attention'] else ('farm_finance_volume_or_overdue' if bucket['farm_finance_attention'] else '')
            bucket['lane_sla_hours'] = cls.STAGE_SLA_HOURS.get(role, 24)
            bucket['policy_context_summary'] = {
                'approval_profile': bucket['policy_context_summary'].get('approval_profile'),
                'approval_profile_source': bucket['policy_context_summary'].get('approval_profile_source'),
                'effective_mode': bucket['policy_context_summary'].get('effective_mode'),
            }
            bucket['lane_health'], bucket['attention_severity'], bucket['attention_bucket'] = cls._queue_health(
                blockers={
                    'remote_review_blocked': bucket['remote_review_blocked'],
                    'attachment_scan_blocked': bucket['attachment_scan_blocked'],
                },
                is_overdue=bool(bucket.get('overdue')),
                director_attention=bool(bucket.get('director_attention')),
                farm_finance_attention=bool(bucket.get('farm_finance_attention')),
            )
        buckets.sort(
            key=lambda row: (
                cls.ATTENTION_SEVERITY_ORDER.get(row.get('attention_severity', 'none'), 99),
                -int(row.get('blocked_count', 0)),
                -int(row['overdue']),
                -int(row['count']),
                row['role_label'],
                row['farm_name'],
            )
        )
        return {
            'generated_at': timezone.now().isoformat(),
            'rows': buckets,
            'summary': {
                'total_pending': sum(int(row.get('count', 0)) for row in buckets),
                'director_attention_count': sum(1 for row in buckets if row.get('director_attention')),
                'farm_finance_rows': sum(1 for row in buckets if row.get('role') == ApprovalRule.ROLE_FARM_FINANCE_MANAGER),
                'farm_finance_attention_count': sum(1 for row in buckets if row.get('farm_finance_attention')),
                'sector_rows': sum(1 for row in buckets if row.get('owner_scope') == 'sector'),
                'blocked_rows': sum(1 for row in buckets if row.get('lane_health') == 'blocked'),
                'attention_rows': sum(1 for row in buckets if row.get('lane_health') == 'attention'),
                'healthy_rows': sum(1 for row in buckets if row.get('lane_health') == 'healthy'),
            },
        }

    @classmethod
    def workbench_summary(cls) -> dict:
        payload = cls.role_workbench_snapshot()
        rows = list(payload.get('rows', []))
        return {
            'generated_at': payload.get('generated_at'),
            'summary': {
                **payload.get('summary', {}),
                'rows': len(rows),
                'overdue_rows': sum(1 for row in rows if row.get('overdue')),
                'blocked_rows': sum(1 for row in rows if row.get('lane_health') == 'blocked'),
                'director_attention_count': sum(1 for row in rows if row.get('director_attention')),
            },
        }

    @classmethod
    def attention_feed(cls) -> dict:
        items = []
        pending = ApprovalRequest.objects.filter(
            deleted_at__isnull=True,
            status=ApprovalRequest.STATUS_PENDING,
        ).select_related('farm')
        now = timezone.now()
        for req in pending:
            snapshot = cls.queue_snapshot(req=req)
            if snapshot.get('is_overdue'):
                items.append({
                    'kind': 'approval_overdue',
                    'severity': 'high',
                    'request_id': req.id,
                    'farm_id': req.farm_id,
                    'farm_name': getattr(req.farm, 'name', ''),
                    'role': req.required_role,
                    'role_label': cls.ROLE_LABELS.get(req.required_role, req.required_role),
                    'message': 'pending approval exceeded lane SLA',
                    'attention_bucket': snapshot.get('attention_bucket', 'approval_overdue'),
                    'created_at': snapshot.get('started_at') or req.created_at.isoformat(),
                })
        for row in cls.role_workbench_snapshot().get('rows', []):
            if row.get('role') == ApprovalRule.ROLE_SECTOR_DIRECTOR or row.get('director_attention'):
                items.append({
                    'kind': 'sector_final_attention',
                    'severity': 'critical' if row.get('lane_health') == 'blocked' else 'high',
                    'farm_id': row.get('farm_id'),
                    'farm_name': row.get('farm_name'),
                    'role': row.get('role'),
                    'role_label': row.get('role_label'),
                    'message': row.get('attention_reason') or 'sector final lane requires attention',
                    'sample_request_ids': row.get('sample_request_ids', []),
                    'attention_bucket': row.get('attention_bucket', 'sector_final_attention'),
                    'created_at': row.get('oldest_started_at') or now.isoformat(),
                })
            elif row.get('farm_finance_attention'):
                items.append({
                    'kind': 'farm_finance_volume_attention',
                    'severity': 'medium',
                    'farm_id': row.get('farm_id'),
                    'farm_name': row.get('farm_name'),
                    'role': row.get('role'),
                    'role_label': row.get('role_label'),
                    'message': row.get('attention_reason') or 'farm finance lane requires attention',
                    'sample_request_ids': row.get('sample_request_ids', []),
                    'attention_bucket': row.get('attention_bucket', 'farm_finance_volume_attention'),
                    'created_at': row.get('oldest_started_at') or now.isoformat(),
                })
            if row.get('remote_review_blocked'):
                items.append({
                    'kind': 'remote_review_blocked',
                    'severity': 'critical',
                    'farm_id': row.get('farm_id'),
                    'farm_name': row.get('farm_name'),
                    'role': row.get('role'),
                    'role_label': row.get('role_label'),
                    'message': 'strict finance blocked pending remote review',
                    'sample_request_ids': row.get('sample_request_ids', []),
                    'attention_bucket': 'blocked_by_policy',
                    'created_at': row.get('oldest_started_at') or now.isoformat(),
                })
            if row.get('attachment_scan_blocked'):
                items.append({
                    'kind': 'attachment_runtime_block',
                    'severity': 'critical',
                    'farm_id': row.get('farm_id'),
                    'farm_name': row.get('farm_name'),
                    'role': row.get('role'),
                    'role_label': row.get('role_label'),
                    'message': 'authoritative evidence is pending scan or quarantined',
                    'sample_request_ids': row.get('sample_request_ids', []),
                    'attention_bucket': 'blocked_by_policy',
                    'created_at': row.get('oldest_started_at') or now.isoformat(),
                })
        attachment_runtime = AttachmentPolicyService.security_runtime_summary()
        if attachment_runtime.get('pending_scan') or attachment_runtime.get('quarantined'):
            items.append({
                'kind': 'attachment_runtime_block',
                'severity': 'high',
                'message': 'attachment runtime requires security review',
                'pending_scan': attachment_runtime.get('pending_scan', 0),
                'quarantined': attachment_runtime.get('quarantined', 0),
                'attention_bucket': 'attachment_runtime_block',
                'created_at': now.isoformat(),
            })
        items.sort(
            key=lambda item: (
                cls.ATTENTION_SEVERITY_ORDER.get(item.get('severity', 'none'), 99),
                item.get('created_at') or '',
            )
        )
        return {
            'generated_at': now.isoformat(),
            'count': len(items),
            'items': items,
        }

    @classmethod
    def sector_dashboard_snapshot(cls) -> dict:
        pending_qs = ApprovalRequest.objects.filter(
            deleted_at__isnull=True,
            status=ApprovalRequest.STATUS_PENDING,
        ).select_related('farm')
        workbench = cls.role_workbench_snapshot()
        maintenance = cls.maintenance_summary()
        attention = cls.attention_feed()

        overdue_buckets = {'overdue': 0, 'on_track': 0}
        blocked_buckets = Counter()
        top_farms = defaultdict(
            lambda: {
                'farm_id': None,
                'farm_name': '',
                'pending_count': 0,
                'blocked_count': 0,
                'overdue_count': 0,
            }
        )
        for req in pending_qs:
            snap = cls.queue_snapshot(req=req)
            farm_bucket = top_farms[req.farm_id]
            farm_bucket['farm_id'] = req.farm_id
            farm_bucket['farm_name'] = getattr(req.farm, 'name', '')
            farm_bucket['pending_count'] += 1
            if snap.get('is_overdue'):
                overdue_buckets['overdue'] += 1
                farm_bucket['overdue_count'] += 1
            else:
                overdue_buckets['on_track'] += 1
            blockers = list(snap.get('blockers', []))
            if blockers:
                farm_bucket['blocked_count'] += 1
            for blocker in blockers:
                blocked_buckets[blocker] += 1

        top_lanes = sorted(
            [
                {
                    'role': row.get('role'),
                    'role_label': row.get('role_label'),
                    'farm_id': row.get('farm_id'),
                    'farm_name': row.get('farm_name'),
                    'count': row.get('count', 0),
                    'overdue': row.get('overdue', 0),
                    'blocked_count': row.get('blocked_count', 0),
                    'lane_health': row.get('lane_health'),
                    'attention_bucket': row.get('attention_bucket'),
                    'attention_reason': row.get('attention_reason'),
                    'director_attention': bool(row.get('director_attention')),
                }
                for row in workbench.get('rows', [])
            ],
            key=lambda row: (
                0 if row.get('lane_health') == 'blocked' else 1 if row.get('lane_health') == 'attention' else 2,
                -row.get('overdue', 0),
                -row.get('count', 0),
            ),
        )[:10]
        top_farm_rows = sorted(
            top_farms.values(),
            key=lambda row: (-row['blocked_count'], -row['pending_count'], -row['overdue_count'], row['farm_name']),
        )[:10]
        return {
            'generated_at': timezone.now().isoformat(),
            'kpis': {
                'pending_requests': pending_qs.count(),
                'overdue_requests': maintenance.get('overdue_requests', 0),
                'blocked_requests': sum(blocked_buckets.values()) if blocked_buckets else 0,
                'strict_finance_pending': maintenance.get('strict_finance_pending', 0),
                'remote_review_blocked': maintenance.get('remote_review_blocked_requests', 0),
                'attachment_runtime_blocked': maintenance.get('attachment_scan_blocked_requests', 0),
                'director_attention_count': sum(1 for row in workbench.get('rows', []) if row.get('director_attention')),
                'final_attention_count': sum(
                    1 for row in workbench.get('rows', [])
                    if row.get('attention_bucket') == 'sector_final_attention'
                ),
            },
            'lane_counts_by_role': workbench.get('summary', {}).get('by_role', {}),
            'overdue_buckets': overdue_buckets,
            'blocked_buckets': dict(blocked_buckets),
            'top_lanes': top_lanes,
            'top_farms': top_farm_rows,
            'attention_summary': {
                'count': attention.get('count', 0),
                'by_kind': dict(Counter(item.get('kind') for item in attention.get('items', []))),
            },
        }

    @classmethod
    def policy_impact_snapshot(cls) -> dict:
        pending_qs = ApprovalRequest.objects.filter(
            deleted_at__isnull=True,
            status=ApprovalRequest.STATUS_PENDING,
        ).select_related('farm')
        farm_ids = list(pending_qs.values_list('farm_id', flat=True).distinct())
        approval_profile_counts = Counter()
        approval_profile_source_counts = Counter()
        threshold_driven_escalations = Counter()
        source_drift = []
        affected_farms = []
        strict_finance_farms = set()
        remote_review_farms = set()
        attachment_strict_farms = set()

        for farm_id in farm_ids:
            req = pending_qs.filter(farm_id=farm_id).first()
            farm = req.farm
            settings_obj = cls._settings_for_farm(farm)
            policy_summary = PolicyEngineService.effective_policy_summary_for_farm(farm=farm, settings_obj=settings_obj)
            flat_policy = policy_summary.get('flat_policy', {})
            source = policy_summary.get('source') or 'farm_settings'
            approval_profile = flat_policy.get('approval_profile') or getattr(settings_obj, 'approval_profile', '')
            approval_profile_counts[approval_profile] += 1
            approval_profile_source_counts[source] += 1
            if approval_profile == FarmSettings.APPROVAL_PROFILE_STRICT_FINANCE:
                strict_finance_farms.add(farm.id)
            if flat_policy.get('weekly_remote_review_required'):
                remote_review_farms.add(farm.id)
            if flat_policy.get('attachment_require_clean_scan_for_strict'):
                attachment_strict_farms.add(farm.id)
            if source != 'farm_settings':
                source_drift.append(
                    {
                        'farm_id': farm.id,
                        'farm_name': farm.name,
                        'policy_source': source,
                        'approval_profile': approval_profile,
                    }
                )
            affected_farms.append(
                {
                    'farm_id': farm.id,
                    'farm_name': farm.name,
                    'effective_mode': flat_policy.get('mode'),
                    'approval_profile': approval_profile,
                    'approval_profile_source': source,
                    'strict_finance_required': approval_profile == FarmSettings.APPROVAL_PROFILE_STRICT_FINANCE,
                    'remote_review_required': bool(flat_policy.get('weekly_remote_review_required')),
                    'attachment_strict': bool(flat_policy.get('attachment_require_clean_scan_for_strict')),
                }
            )

        for req in pending_qs:
            snap = cls.queue_snapshot(req=req)
            threshold_reason = (snap.get('policy_context') or {}).get('threshold_reason')
            if threshold_reason:
                threshold_driven_escalations[threshold_reason] += 1

        return {
            'generated_at': timezone.now().isoformat(),
            'approval_profile_counts': dict(approval_profile_counts),
            'approval_profile_source_counts': dict(approval_profile_source_counts),
            'threshold_driven_escalations': dict(threshold_driven_escalations),
            'policy_source_drift_count': len(source_drift),
            'policy_source_drift': source_drift,
            'strict_finance_farms_count': len(strict_finance_farms),
            'remote_review_farms_count': len(remote_review_farms),
            'attachment_strict_farms_count': len(attachment_strict_farms),
            'affected_farms': affected_farms,
        }

    @classmethod
    def farm_governance_snapshot(cls, *, farm_id: int) -> dict:
        pending_qs = ApprovalRequest.objects.filter(
            deleted_at__isnull=True,
            status=ApprovalRequest.STATUS_PENDING,
            farm_id=farm_id,
        ).select_related('farm')
        any_req = pending_qs.first() or ApprovalRequest.objects.select_related('farm').filter(
            deleted_at__isnull=True,
            farm_id=farm_id,
        ).first()
        if any_req is None:
            from smart_agri.core.models import Farm

            farm = Farm.objects.filter(pk=farm_id, deleted_at__isnull=True).first()
            if farm is None:
                raise ValidationError("Farm not found for governance snapshot.")
        else:
            farm = any_req.farm
        settings_obj = cls._settings_for_farm(farm)
        policy_summary = PolicyEngineService.effective_policy_summary_for_farm(farm=farm, settings_obj=settings_obj)
        lane_rows = [row for row in cls.role_workbench_snapshot().get('rows', []) if row.get('farm_id') == farm_id]
        blocker_counts = Counter()
        overdue_requests = 0
        for req in pending_qs:
            snap = cls.queue_snapshot(req=req)
            if snap.get('is_overdue'):
                overdue_requests += 1
            for blocker in snap.get('blockers', []):
                blocker_counts[blocker] += 1

        activation_requests = []
        exception_requests = []
        if PolicyEngineService.policy_engine_schema_available():
            activation_requests = list(
                PolicyActivationRequest.objects.filter(farm_id=farm_id)
                .order_by('-created_at')
                .values('id', 'status', 'effective_from', 'created_at')
            )
            exception_requests = list(
                PolicyExceptionRequest.objects.filter(farm_id=farm_id)
                .order_by('-created_at')
                .values('id', 'status', 'policy_fields', 'effective_from', 'effective_to', 'created_at')
            )

        return {
            'generated_at': timezone.now().isoformat(),
            'farm_id': farm.id,
            'farm_name': farm.name,
            'effective_mode': getattr(settings_obj, 'mode', None),
            'approval_profile': getattr(settings_obj, 'approval_profile', None),
            'approval_profile_source': policy_summary.get('source'),
            'lane_summary': {
                'rows': lane_rows,
                'row_count': len(lane_rows),
                'pending_requests': pending_qs.count(),
                'overdue_requests': overdue_requests,
            },
            'active_blockers': dict(blocker_counts),
            'open_activation_requests': activation_requests,
            'open_exception_requests': exception_requests,
            'remote_review_posture': {
                'remote_site': bool(getattr(settings_obj, 'remote_site', False)),
                'weekly_remote_review_required': bool(getattr(settings_obj, 'weekly_remote_review_required', False)),
                'remote_review_blocked_requests': blocker_counts.get('remote_review_blocked', 0),
            },
            'attachment_runtime_posture': {
                'attachment_scan_mode': getattr(settings_obj, 'attachment_scan_mode', None),
                'attachment_require_clean_scan_for_strict': bool(getattr(settings_obj, 'attachment_require_clean_scan_for_strict', False)),
                'attachment_scan_blocked_requests': blocker_counts.get('attachment_scan_blocked', 0),
            },
            'policy_summary': policy_summary,
        }

    @classmethod
    def farm_ops_snapshot(cls, *, farm_id: int, outbox_limit: int = 25, attachment_limit: int = 25) -> dict:
        governance = cls.farm_governance_snapshot(farm_id=farm_id)
        runtime_detail = cls.runtime_governance_detail_snapshot(limit=100)
        runtime_detail["detail_rows"] = [
            row for row in runtime_detail.get("detail_rows", [])
            if row.get("farm_id") == farm_id
        ]
        runtime_detail["filtered_total"] = len(runtime_detail["detail_rows"])
        return {
            "generated_at": timezone.now().isoformat(),
            "farm_id": farm_id,
            "farm_name": governance.get("farm_name", ""),
            "governance": governance,
            "runtime_governance": runtime_detail,
            "outbox": OpsHealthService.integration_outbox_detail_snapshot(farm_id=farm_id, limit=outbox_limit),
            "attachment_runtime": OpsHealthService.attachment_runtime_detail_snapshot(farm_id=farm_id, limit=attachment_limit),
            "release_health": OpsHealthService.release_health_snapshot(),
        }

    @classmethod
    def request_trace(
        cls,
        *,
        request_id: int | None = None,
        correlation_id: str | None = None,
    ) -> dict:
        req = None
        if request_id is not None:
            req = ApprovalRequest.objects.filter(
                pk=request_id,
                deleted_at__isnull=True,
            ).select_related("farm", "requested_by", "approved_by", "cost_center").prefetch_related("stage_events__actor").first()
        if req is None and correlation_id:
            outbox_query = (
                Q(metadata__approval_request_id=str(correlation_id))
                | Q(metadata__correlation_id=str(correlation_id))
                | (Q(aggregate_type="ApprovalRequest") & Q(aggregate_id=str(correlation_id)))
            )
            if request_id is not None:
                outbox_query |= Q(metadata__approval_request_id=request_id)
            outbox_event = IntegrationOutboxEvent.objects.filter(outbox_query).order_by("-created_at").first()
            if outbox_event and str(outbox_event.aggregate_id).isdigit():
                req = ApprovalRequest.objects.filter(
                    pk=int(outbox_event.aggregate_id),
                    deleted_at__isnull=True,
                ).select_related("farm", "requested_by", "approved_by", "cost_center").prefetch_related("stage_events__actor").first()
        if req is None:
            raise ValidationError("Approval request not found for trace view.")

        queue_snapshot = cls.queue_snapshot(req=req)
        workflow_blueprint = cls.workflow_blueprint_for_request(req=req)
        stage_events = cls.stage_events_payload(req=req)
        linked_outbox = list(
            IntegrationOutboxEvent.objects.filter(
                Q(metadata__approval_request_id=req.id)
                | (Q(aggregate_type="ApprovalRequest") & Q(aggregate_id=str(req.id)))
                | (Q(metadata__correlation_id=str(correlation_id)) if correlation_id else Q(pk__isnull=True))
            )
            .select_related("farm")
            .order_by("-created_at")[:10]
            .values(
                "id",
                "event_id",
                "event_type",
                "destination",
                "status",
                "attempts",
                "max_attempts",
                "available_at",
                "created_at",
                "last_error",
                "farm_id",
                "metadata",
            )
        )
        resolved_correlation = (
            correlation_id
            or next(
                (
                    (row.get("metadata") or {}).get("correlation_id")
                    for row in linked_outbox
                    if (row.get("metadata") or {}).get("correlation_id")
                ),
                None,
            )
            or f"approval-request-{req.id}"
        )
        logger.info(
            "ops.trace.viewed",
            extra={
                "trace_kind": "approval_request",
                "approval_request_id": req.id,
                "correlation_id": resolved_correlation,
            },
        )
        return {
            "generated_at": timezone.now().isoformat(),
            "correlation_id": resolved_correlation,
            "request": {
                "id": req.id,
                "farm_id": req.farm_id,
                "farm_name": getattr(req.farm, "name", ""),
                "module": req.module,
                "action": req.action,
                "status": req.status,
                "requested_amount": str(req.requested_amount or Decimal("0.0000")),
                "required_role": req.required_role,
                "required_role_label": cls.ROLE_LABELS.get(req.required_role, req.required_role),
                "final_required_role": req.final_required_role,
                "current_stage": req.current_stage,
                "total_stages": req.total_stages,
                "requester_name": getattr(req.requested_by, "username", ""),
                "approver_name": getattr(req.approved_by, "username", ""),
                "created_at": req.created_at.isoformat() if req.created_at else None,
                "updated_at": req.updated_at.isoformat() if req.updated_at else None,
            },
            "queue_snapshot": queue_snapshot,
            "workflow_blueprint": workflow_blueprint,
            "stage_events": stage_events,
            "policy_context": queue_snapshot.get("policy_context", {}),
            "blockers": queue_snapshot.get("blockers", []),
            "linked_outbox_events": linked_outbox,
        }

    @staticmethod
    def _append_history(*, req: ApprovalRequest, user, decision: str, role: str, note: str = "") -> list:
        return append_history(req=req, user=user, decision=decision, role=role, note=note)

    @staticmethod
    def _record_stage_event(*, req: ApprovalRequest, user, action_type: str, role: str, note: str = "") -> ApprovalStageEvent:
        return record_stage_event(req=req, user=user, action_type=action_type, role=role, note=note)

    @staticmethod
    def stage_events_payload(*, req: ApprovalRequest) -> list[dict]:
        return build_stage_events_payload(req=req, role_labels=ApprovalGovernanceService.ROLE_LABELS)

    @staticmethod
    def _mark_authoritative_request_evidence(req: ApprovalRequest) -> None:
        target = req.transaction_source
        if target is None:
            return
        farm_settings = FarmSettings.objects.filter(farm_id=req.farm_id).first()
        attachments = []
        if isinstance(target, Attachment):
            attachments = [target]
        elif hasattr(target, "attachment") and getattr(target, "attachment", None):
            attachments = [getattr(target, "attachment")]
        elif hasattr(target, "attachments"):
            related = getattr(target, "attachments")
            if hasattr(related, "all"):
                attachments = list(related.all())
        for attachment in attachments:
            AttachmentPolicyService.mark_authoritative_after_approval(
                attachment=attachment,
                farm_settings=farm_settings,
                approved_at=timezone.now(),
            )
            attachment.save(update_fields=[
                "is_authoritative_evidence",
                "evidence_class",
                "expires_at",
                "archived_at",
                "storage_tier",
                "archive_backend",
                "archive_key",
                "content_type",
                "malware_scan_status",
                "quarantine_reason",
                "scanned_at",
                "quarantined_at",
                "updated_at",
            ])

    @staticmethod
    def _resolve_required_role(*, farm, module, action_name, cost_center, amount: Decimal) -> str:
        qs = ApprovalRule.objects.filter(
            farm=farm,
            module=module,
            action=action_name,
            is_active=True,
            min_amount__lte=amount,
            deleted_at__isnull=True,
        )
        qs = qs.filter(Q(max_amount__isnull=True) | Q(max_amount__gte=amount))
        if cost_center:
            qs = qs.filter(Q(cost_center=cost_center) | Q(cost_center__isnull=True))
        else:
            qs = qs.filter(cost_center__isnull=True)

        rule = qs.order_by(F("cost_center").asc(nulls_last=True), "-min_amount").first()
        if rule:
            return rule.required_role

        settings = getattr(farm, "settings", None)
        farm_tier = (getattr(farm, "tier", None) or "SMALL").upper()
        local_threshold = getattr(settings, "local_finance_threshold", Decimal("100000.0000")) if settings else Decimal("100000.0000")
        sector_review_threshold = getattr(settings, "sector_review_threshold", Decimal("250000.0000")) if settings else Decimal("250000.0000")
        committee_threshold = getattr(settings, "procurement_committee_threshold", Decimal("500000.0000")) if settings else Decimal("500000.0000")
        single_officer = bool(getattr(settings, "single_finance_officer_allowed", False)) if settings else False

        if farm_tier == "SMALL" and single_officer and amount <= local_threshold:
            return ApprovalRule.ROLE_FARM_FINANCE_MANAGER
        if amount <= local_threshold:
            return ApprovalRule.ROLE_FARM_FINANCE_MANAGER
        if amount <= sector_review_threshold:
            return ApprovalRule.ROLE_SECTOR_ACCOUNTANT
        if amount <= committee_threshold:
            return ApprovalRule.ROLE_SECTOR_REVIEWER
        if amount <= committee_threshold * Decimal("2"):
            return ApprovalRule.ROLE_CHIEF_ACCOUNTANT
        if amount <= committee_threshold * Decimal("4"):
            return ApprovalRule.ROLE_FINANCE_DIRECTOR
        return ApprovalRule.ROLE_SECTOR_DIRECTOR

    @classmethod
    @transaction.atomic
    def escalate_overdue_requests(cls) -> int:
        count = 0
        for req in cls.overdue_queryset().select_for_update():
            next_role = cls._next_stage_role(final_role=req.final_required_role, current_stage=req.current_stage, farm=req.farm, module=req.module)
            req.approval_history = cls._append_history(
                req=req,
                user=req.requested_by,
                decision='AUTO_ESCALATED',
                role=req.required_role,
                note='Automatic SLA escalation due to overdue pending stage.',
            )
            previous_role = req.required_role
            if next_role is not None:
                req.current_stage = req.current_stage + 1
                req.required_role = next_role
            req.save(update_fields=['approval_history', 'current_stage', 'required_role', 'updated_at'])
            cls._record_stage_event(
                req=req,
                user=req.requested_by,
                action_type=ApprovalStageEvent.ACTION_AUTO_ESCALATED,
                role=previous_role,
                note='Automatic SLA escalation due to overdue pending stage.',
            )
            count += 1
        return count

    @staticmethod
    @transaction.atomic
    def create_rule(*, user, **validated_data) -> ApprovalRule:
        farm = validated_data.get("farm")
        _ensure_user_has_farm_access(user, farm.id if farm else None)
        ApprovalGovernanceService._require_sector_finance_authority(user)
        instance = ApprovalRule(**validated_data)
        instance.full_clean()
        instance.save()
        return instance

    @staticmethod
    @transaction.atomic
    def update_rule(*, user, instance: ApprovalRule, **validated_data) -> ApprovalRule:
        ApprovalGovernanceService._require_sector_finance_authority(user)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.full_clean()
        instance.save()
        return instance

    @staticmethod
    @transaction.atomic
    def create_request(*, user, **validated_data) -> ApprovalRequest:
        farm = validated_data.get("farm")
        _ensure_user_has_farm_access(user, farm.id if farm else None)

        # [AGRI-GUARDIAN Axis 5 / PRD §8.2-8.3 / AGENTS.md Rule#19]
        # MEDIUM and LARGE farms MUST have a designated farm finance manager
        # before any approval request can be created.
        if farm is not None:
            from smart_agri.core.services.farm_tiering_policy_service import FarmTieringPolicyService
            farm_tier = (getattr(farm, 'tier', None) or 'SMALL').upper()
            tier_snapshot = FarmTieringPolicyService.snapshot(farm_tier)
            if tier_snapshot.get('requires_farm_finance_manager', False):
                from smart_agri.finance.services.farm_finance_authority_service import FarmFinanceAuthorityService
                from smart_agri.core.api.permissions import user_has_farm_role
                from smart_agri.accounts.models import FarmMembership
                ffm_roles = FarmFinanceAuthorityService.FARM_FINANCE_MANAGER_ROLES
                has_ffm = FarmMembership.objects.filter(
                    farm=farm,
                    role__in=ffm_roles,
                ).exists()
                if not has_ffm:
                    raise ValidationError(
                        f"مزارع الحجم {tier_snapshot.get('label_ar', farm_tier)} تتطلب تعيين "
                        f"مدير مالي للمزرعة قبل إنشاء طلبات الاعتماد المالي. "
                        f"[PRD §8 / AGENTS.md Rule#19]"
                    )

        amount = validated_data.get("requested_amount") or Decimal("0.0000")
        validated_data["requested_by"] = user
        final_role = ApprovalGovernanceService._resolve_required_role(
            farm=farm,
            module=validated_data.get("module"),
            action_name=validated_data.get("action"),
            cost_center=validated_data.get("cost_center"),
            amount=amount,
        )
        role_chain = ApprovalGovernanceService._build_role_chain(final_role, farm=farm, module=validated_data.get("module"))
        validated_data["required_role"] = role_chain[0]
        validated_data["final_required_role"] = final_role
        validated_data["current_stage"] = 1
        validated_data["total_stages"] = len(role_chain)
        validated_data["approval_history"] = []
        validated_data["status"] = ApprovalRequest.STATUS_PENDING
        instance = ApprovalRequest(**validated_data)
        instance.full_clean()
        instance.save()
        ApprovalGovernanceService._record_stage_event(
            req=instance,
            user=user,
            action_type=ApprovalStageEvent.ACTION_CREATED,
            role=instance.required_role,
            note='Approval request created and queued.',
        )
        return instance

    @classmethod
    def can_approve(cls, user, req: ApprovalRequest) -> bool:
        if getattr(user, "is_superuser", False):
            return True
        return cls._user_has_exact_stage_role(user=user, req=req)

    @staticmethod
    @transaction.atomic
    def approve_request(*, user, request_id: int, note: str = "") -> ApprovalRequest:
        req = ApprovalRequest.objects.select_for_update().get(pk=request_id, deleted_at__isnull=True)
        _ensure_user_has_farm_access(user, req.farm_id)
        if req.status != ApprovalRequest.STATUS_PENDING:
            raise ValidationError("لا يمكن اعتماد إلا الطلبات المعلّقة.")
        if req.requested_by_id == getattr(user, "id", None) and not getattr(user, "is_superuser", False):
            raise PermissionDenied("لا يجوز لمنشئ الطلب اعتماد طلبه نفسه.")
        prior_actor_ids = {entry.get("actor_id") for entry in (req.approval_history or []) if entry.get("actor_id") is not None}
        if getattr(user, "id", None) in prior_actor_ids and not getattr(user, "is_superuser", False):
            raise PermissionDenied("لا يجوز لنفس المستخدم تمرير أكثر من مرحلة في نفس الطلب.")
        if not ApprovalGovernanceService.can_approve(user, req):
            raise PermissionDenied("الاعتماد المرحلي يتطلب الدور المطابق للمرحلة الحالية؛ استخدم override-stage فقط عبر السلطة القطاعية النهائية وبسبب موثق.")
        stage_role = req.required_role
        req.approval_history = ApprovalGovernanceService._append_history(
            req=req,
            user=user,
            decision="APPROVED_STAGE",
            role=stage_role,
            note=(note or "").strip(),
        )
        next_role = ApprovalGovernanceService._next_stage_role(
            final_role=req.final_required_role,
            current_stage=req.current_stage,
            farm=req.farm,
            module=req.module,
        )
        req.rejection_reason = ""
        if next_role is None:
            finalize_request(req=req, user=user)
            req.save(update_fields=[
                "approval_history",
                "status",
                "approved_by",
                "approved_at",
                "rejection_reason",
                "updated_at",
            ])
            ApprovalGovernanceService._record_stage_event(
                req=req,
                user=user,
                action_type=ApprovalStageEvent.ACTION_FINAL_APPROVED,
                role=stage_role,
                note=((note or '').strip() or 'Final approval completed.'),
            )
            ApprovalGovernanceService._mark_authoritative_request_evidence(req)
            return req

        req.current_stage = req.current_stage + 1
        req.required_role = next_role
        req.save(update_fields=[
            "approval_history",
            "current_stage",
            "required_role",
            "rejection_reason",
            "updated_at",
        ])
        ApprovalGovernanceService._record_stage_event(
            req=req,
            user=user,
            action_type=ApprovalStageEvent.ACTION_STAGE_APPROVED,
            role=stage_role,
            note=((note or '').strip() or f'Stage passed to {next_role}.'),
        )
        return req

    @staticmethod
    @transaction.atomic
    def override_request(*, user, request_id: int, reason: str) -> ApprovalRequest:
        req = ApprovalRequest.objects.select_for_update().get(pk=request_id, deleted_at__isnull=True)
        _ensure_user_has_farm_access(user, req.farm_id)
        if req.status != ApprovalRequest.STATUS_PENDING:
            raise ValidationError("لا يمكن override إلا على الطلبات المعلّقة.")
            
        if req.requested_by_id == getattr(user, "id", None) and not getattr(user, "is_superuser", False):
            raise PermissionDenied("لا يجوز لمنشئ الطلب اعتماد طلبه نفسه عبر الـ override.")
        prior_actor_ids = {entry.get("actor_id") for entry in (req.approval_history or []) if entry.get("actor_id") is not None}
        if getattr(user, "id", None) in prior_actor_ids and not getattr(user, "is_superuser", False):
            raise PermissionDenied("لا يجوز لنفس المستخدم تمرير أكثر من مرحلة في نفس الطلب عبر الـ override.")

        if ApprovalGovernanceService.can_approve(user, req):
            raise ValidationError("المستخدم يملك الدور المطابق للمرحلة الحالية؛ استخدم الاعتماد المرحلي العادي بدل override.")
        if not ApprovalGovernanceService.can_override_stage(user, req):
            raise PermissionDenied("override-stage يتطلب سلطة قطاعية نهائية موثقة.")
        reason = str(reason or '').strip()
        if not reason:
            raise ValidationError("سبب override مطلوب.")
        stage_role = req.required_role
        req.approval_history = ApprovalGovernanceService._append_history(
            req=req,
            user=user,
            decision="OVERRIDDEN_STAGE",
            role=stage_role,
            note=reason,
        )
        next_role = ApprovalGovernanceService._next_stage_role(
            final_role=req.final_required_role,
            current_stage=req.current_stage,
            farm=req.farm,
            module=req.module,
        )
        req.rejection_reason = ""
        if next_role is None:
            finalize_request(req=req, user=user)
            req.save(update_fields=["approval_history", "status", "approved_by", "approved_at", "rejection_reason", "updated_at"])
            ApprovalGovernanceService._record_stage_event(
                req=req,
                user=user,
                action_type=ApprovalStageEvent.ACTION_OVERRIDDEN,
                role=stage_role,
                note=reason,
            )
            ApprovalGovernanceService._mark_authoritative_request_evidence(req)
            return req
        req.current_stage = req.current_stage + 1
        req.required_role = next_role
        req.save(update_fields=["approval_history", "current_stage", "required_role", "rejection_reason", "updated_at"])
        ApprovalGovernanceService._record_stage_event(
            req=req,
            user=user,
            action_type=ApprovalStageEvent.ACTION_OVERRIDDEN,
            role=stage_role,
            note=reason,
        )
        return req

    @staticmethod
    @transaction.atomic
    def reopen_request(*, user, request_id: int, reason: str = "") -> ApprovalRequest:
        req = ApprovalRequest.objects.select_for_update().get(pk=request_id, deleted_at__isnull=True)
        _ensure_user_has_farm_access(user, req.farm_id)
        if req.status != ApprovalRequest.STATUS_REJECTED:
            raise ValidationError("فقط الطلبات المرفوضة يمكن إعادة فتحها.")
        if req.requested_by_id != getattr(user, 'id', None) and not ApprovalGovernanceService.can_override_stage(user, req):
            raise PermissionDenied("إعادة الفتح متاحة لمنشئ الطلب أو لسلطة قطاعية نهائية.")
        chain = ApprovalGovernanceService._build_role_chain(req.final_required_role, farm=req.farm, module=req.module)
        reopen_request_state(req=req, initial_role=chain[0], total_stages=len(chain))
        req.approval_history = ApprovalGovernanceService._append_history(
            req=req,
            user=user,
            decision="REOPENED",
            role=req.required_role,
            note=(reason or '').strip(),
        )
        req.save(update_fields=[
            "status", "current_stage", "total_stages", "required_role", "approved_by", "approved_at", "rejection_reason", "approval_history", "updated_at"
        ])
        ApprovalGovernanceService._record_stage_event(
            req=req,
            user=user,
            action_type=ApprovalStageEvent.ACTION_REOPENED,
            role=req.required_role,
            note=(reason or '').strip() or 'Request reopened to stage 1.',
        )
        return req

    @staticmethod
    @transaction.atomic
    def reject_request(*, user, request_id: int, reason: str) -> ApprovalRequest:
        req = ApprovalRequest.objects.select_for_update().get(pk=request_id, deleted_at__isnull=True)
        _ensure_user_has_farm_access(user, req.farm_id)
        if req.status != ApprovalRequest.STATUS_PENDING:
            raise ValidationError("لا يمكن رفض إلا الطلبات المعلّقة.")
        if not ApprovalGovernanceService.can_approve(user, req):
            raise PermissionDenied("ليس لديك صلاحية رفض هذا الطلب.")
        reason = str(reason or "").strip()
        if not reason:
            raise ValidationError("سبب الرفض مطلوب.")
        req.approval_history = ApprovalGovernanceService._append_history(
            req=req,
            user=user,
            decision="REJECTED",
            role=req.required_role,
            note=reason,
        )
        reject_request_state(req=req, user=user, reason=reason)
        req.save(update_fields=["approval_history", "status", "approved_by", "approved_at", "rejection_reason", "updated_at"])
        ApprovalGovernanceService._record_stage_event(
            req=req,
            user=user,
            action_type=ApprovalStageEvent.ACTION_REJECTED,
            role=req.required_role,
            note=reason,
        )
        return req

