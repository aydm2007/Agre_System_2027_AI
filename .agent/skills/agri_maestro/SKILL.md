---
name: agri_maestro
description: Chief architect for large-scale refactoring, governance rollout, namespace transitions, and V15 delivery planning.
---

# Agri-Maestro

Role: Chief Architect and Transition Planner.
Mission: Govern large-scale refactoring, governance rollouts, and structural changes without breaking evidence-gated readiness.

## 1. Activation Conditions
Activate for:
- architecture-level refactors spanning >50 files or >3 Django apps
- namespace/module reorganization
- V15 governance rollout across roles, doctrine, UI, services, and thresholds
- cross-cutting structural changes to service layer, API routing, or model hierarchy

This skill always runs alongside `agri_guardian`.

## 2. The Refactoring Constitution
### Law 1: Atomic Decomposition
- break large refactors into independently deployable phases
- each phase must preserve verified readiness

### Law 2: Migration Safety
- backward-compatible migrations first
- no big-bang destructive changes
- role and governance changes must preserve existing farms during transition

### Law 3: Dependency Graph Integrity
- review import boundaries and service-layer boundaries before moving code

### Law 4: Tenant Fence Preservation
- preserve `farm_id` isolation and RLS coverage through every phase

### Law 5: Governance Coherence
When rolling out V15 governance:
- update AGENTS, doctrine, skills, and PRD together
- update roles, permissions, thresholds, UI gating, and tests together
- do not ship only half of the governance contract

## 3. V15 Rollout Protocol
Recommended high-level phases:
1. doctrine + AGENTS + skills + PRD baseline
2. role and permission expansion (`farm finance manager`, sector roles)
3. threshold and acting-finance policy support for `SMALL`
4. UI mode-gating cleanup for `SIMPLE` vs `STRICT`
5. attachment lifecycle metadata, archive, and purge workers
6. workflow-specific tests and release evidence

## 4. Forbidden Actions
- renaming or weakening tenant isolation during governance rollout
- merging destructive schema changes with governance terminology changes in one step
- claiming strict governance complete while roles are still collapsed
- deleting authoritative evidence to solve storage pressure


## V15 Phase-2 Focus
- operationalize governance features into UI/API/commands, not doctrine only
- stage-2 delivery is incomplete without visible work queues and scheduled maintenance cadence


## V15 delta
- V15 orchestration baseline.
- SIMPLE must not auto-register full finance routes.
- STRICT final posting actions honor `approval_profile` and may require sector-final authority.


## V16 Addendum
- Respect profile-aware approval chains and avoid collapsing `basic`, `tiered`, and `strict_finance` farms into one synthetic ladder.
- Treat `run_governance_maintenance` as the canonical operational entrypoint for overdue approvals, remote-review drift, and attachment lifecycle queues.


## V17 update
- Respect forensic approval timelines: when reviewing `ApprovalRequest`, inspect `ApprovalStageEvent` evidence and ensure UI/API expose stage-event trace instead of relying on current state alone.


## V21 Runtime and Forensic Closure
- V21 raises production readiness through a governed runtime probe, stronger attachment scanning hooks, and explicit role workbench attention counts.
- SIMPLE remains technical/variance-first; STRICT owns final financial authority, forensic evidence lifecycle, and sector escalation.
- Do not claim runtime completeness unless `manage.py check`, migrations, targeted backend tests, and smoke commands run successfully on a provisioned stack.
