from __future__ import annotations

from django.utils import timezone

from smart_agri.finance.models import ApprovalStageEvent


def append_history(*, req, user, decision: str, role: str, note: str = "") -> list:
    history = list(req.approval_history or [])
    history.append(
        {
            "stage": req.current_stage,
            "role": role,
            "decision": decision,
            "actor_id": getattr(user, "id", None),
            "actor_username": getattr(user, "username", ""),
            "at": timezone.now().isoformat(),
            "note": note or "",
        }
    )
    return history


def record_stage_event(*, req, user, action_type: str, role: str, note: str = "") -> ApprovalStageEvent:
    return ApprovalStageEvent.objects.create(
        request=req,
        stage_number=req.current_stage,
        role=role,
        action_type=action_type,
        actor=user,
        note=(note or "")[:500],
        snapshot={
            'request_status': req.status,
            'current_stage': req.current_stage,
            'total_stages': req.total_stages,
            'required_role': req.required_role,
            'final_required_role': req.final_required_role,
        },
    )


def stage_events_payload(*, req, role_labels: dict[str, str]) -> list[dict]:
    rows = []
    for event in req.stage_events.select_related('actor').all()[:25]:
        rows.append({
            'id': event.id,
            'stage_number': event.stage_number,
            'role': event.role,
            'role_label': role_labels.get(event.role, event.role),
            'action_type': event.action_type,
            'actor_id': event.actor_id,
            'actor_username': getattr(event.actor, 'username', '') if event.actor_id else '',
            'note': event.note,
            'created_at': event.created_at.isoformat() if event.created_at else None,
        })
    return rows


def finalize_request(*, req, user):
    req.status = req.STATUS_APPROVED
    req.approved_by = user
    req.approved_at = timezone.now()
    return req


def reopen_request_state(*, req, initial_role: str, total_stages: int):
    req.status = req.STATUS_PENDING
    req.current_stage = 1
    req.total_stages = total_stages
    req.required_role = initial_role
    req.approved_by = None
    req.approved_at = None
    req.rejection_reason = ""
    return req


def reject_request_state(*, req, user, reason: str):
    req.status = req.STATUS_REJECTED
    req.approved_by = user
    req.approved_at = timezone.now()
    req.rejection_reason = reason
    return req
