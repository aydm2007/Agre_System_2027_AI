# V17 Strict Assessment (2026-03-16)

## Honest score
- **V16:** 93.2/100
- **V17:** **93.8/100**

## What improved for real
1. **Forensic approval trace**: `ApprovalStageEvent` adds append-only event evidence for `CREATED`, `STAGE_APPROVED`, `FINAL_APPROVED`, `REJECTED`, and `AUTO_ESCALATED`.
2. **Approval API / UI visibility**: request serializer now exposes `stage_events`; `timeline` endpoint exists; Approval Inbox renders recent stage-event evidence.
3. **Service-layer evidence generation**: stage events are recorded in create/approve/reject/escalate service flows, not only in frontend state.
4. **Reference contract refresh**: `AGENTS.md`, skills, doctrine, and PRD now reflect forensic timeline requirements.

## What was actually verified
- `python -m compileall backend`
- `scripts/verification/check_compliance_docs.py`
- `scripts/verification/check_no_bare_exceptions.py`
- `backend/scripts/check_idempotency_actions.py`
- `backend/scripts/check_no_float_mutations.py`
- DOCX render QA for the V17 PRD

## Why V17 is not 95+ yet
- No Django runtime/test execution in this environment.
- Approval workflow is more auditable, but still not a fully dynamic data-driven BPM/workflow engine.
- Attachment security still lacks production-grade AV/CDR/object-storage lifecycle proof.
- Farm finance manager authority still needs deeper end-to-end enforcement across every strict cycle.
- No verified scheduler/worker proof for maintenance commands in a live deployment environment.

## Next gap-closure focus
1. Run Django migrations + checks + targeted tests in a real environment.
2. Add event-driven approval inbox ownership/SLA transitions with richer delegation rules.
3. Deepen strict-cycle farm finance manager enforcement in all posting services.
4. Add production-grade attachment security pipeline and object-storage lifecycle proof.
