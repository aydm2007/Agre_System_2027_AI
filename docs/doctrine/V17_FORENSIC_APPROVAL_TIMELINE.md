# V17 Forensic Approval Timeline

## Objective
Provide event-level evidence for `ApprovalRequest` so approval posture is no longer inferred only from mutable current-state fields.

## What changed
- Added `ApprovalStageEvent` as append-only stage evidence.
- Each request now records at least a `CREATED` event.
- Approvals, rejections, and automatic escalations append stage events.
- API exposes `timeline` and inline `stage_events` for operational/forensic review.
- Approval Inbox surfaces the latest stage-event evidence for field and sector teams.

## Why it matters
- improves forensic traceability
- supports maker/checker review
- makes overdue escalation auditable
- reduces ambiguity between queue state and historical approval evidence
