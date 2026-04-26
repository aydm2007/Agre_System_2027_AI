# Release Governance Standard

## Environment Segregation
- Dev: local development and experimentation.
- Staging: pre-release validation with full release gates.
- Production: controlled deployment only after evidence-complete approval.

## Change Approval Workflow
1. Open PR with impact statement and evidence summary.
2. Mandatory checks PASS (functional + non-functional gates).
3. Technical approval by code owner.
4. Compliance approval when financial/inventory/governance scope changes.

## Emergency Change Policy
- Emergency changes are allowed only for service restoration.
- Must include:
  - incident reference
  - risk assessment
  - rollback plan
  - postmortem within 48 hours

## Merge Blocking Conditions
- Missing mandatory compliance documents.
- Missing or stale DR drill evidence.
- Missing control matrix mappings for new critical controls.
- Any failed mandatory release gate command from `AGENTS.md`.

## Evidence Requirements per Release
- Baseline gap register updated.
- Global readiness evidence report updated.
- DR drill evidence current (<= 31 days).
- CI output references for functional and non-functional gates.
