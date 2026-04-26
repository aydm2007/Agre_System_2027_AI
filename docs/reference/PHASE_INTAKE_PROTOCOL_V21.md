# Phase Intake Protocol (V21)

## Purpose

This protocol makes `AGENTS.md` the required entry point for every future phase without turning it into a competing authority above the `PRD`.

The rule is:

1. Start from `AGENTS.md`
2. Resolve the active authority set from what `AGENTS.md` points to
3. Read only the references needed for the current phase
4. Compare the target change against current canonical evidence before planning or implementation

This protocol is intake and planning guidance. It does not replace:

- `docs/prd/AGRIASSET_V21_MASTER_PRD_AR.md`
- `AGENTS.md`
- `docs/reference/REFERENCE_MANIFEST_V21.yaml`
- `docs/reference/REFERENCE_PRECEDENCE_AND_OVERRIDE_V21.md`

## Governing Rule

`AGENTS.md` is the first reading surface for future phases because it tells the operator:

- what the system is
- what the non-negotiables are
- which contracts are active
- how evidence gating works
- which references and skills are canonical

But `AGENTS.md` itself declares that product truth remains governed by the `PRD`, and that manifest plus precedence files govern reference loading and conflict resolution.

## Mandatory Intake Sequence

Every new phase must start in this order:

1. Read `AGENTS.md`
2. Extract the phase-relevant sections from `AGENTS.md`
3. Read `docs/prd/AGRIASSET_V21_MASTER_PRD_AR.md`
4. Read `docs/reference/REFERENCE_MANIFEST_V21.yaml`
5. Read `docs/reference/REFERENCE_PRECEDENCE_AND_OVERRIDE_V21.md`
6. Read only the doctrine, matrices, and canonical skills relevant to the phase
7. Read current canonical evidence under `docs/evidence/closure/latest/`
8. Only then define the target delta

## What Must Be Extracted From AGENTS

At intake time, the phase owner must explicitly extract:

- the governing contracts relevant to the phase
- the non-negotiables that cannot be broken
- the affected workflows or axes
- the applicable mode rules for `SIMPLE` and `STRICT`
- the applicable governance layer:
  - farm
  - sector
  - attachment
  - operational runtime
  - reference integrity

This avoids free-form planning from code impressions alone.

## Phase Classification

Every phase must be classified before planning. Use exactly one primary class:

- `product_change`
- `governance_policy_change`
- `observability_ops_change`
- `reference_doc_alignment`

Optional secondary tags may be added only if they do not blur ownership.

## Active Authority Set

Each phase plan must declare an `Active Authority Set` derived from intake. It must include:

- `PRD`
- `AGENTS.md`
- manifest and precedence references
- only the doctrine and matrices relevant to the phase
- current canonical evidence

Historical reports may be used for traceability only. They must not be used as higher authority than current canonical evidence.

## Required Planning Shape

Every future phase plan must contain these sections:

- `Reference Entry`
- `Active Authority Set`
- `Current Proven State`
- `Target Delta`
- `Non-Negotiables`
- `Acceptance`

Minimum content for each section:

### Reference Entry

- which `AGENTS.md` sections govern this phase
- whether a deeper `AGENTS.md` exists in the target subtree

### Active Authority Set

- exact governing files for the phase
- any canonical skills used as execution lenses

### Current Proven State

- current canonical gate state
- current canonical axis state
- any known blockers or debt explicitly relevant to the phase

### Target Delta

- what changes
- what does not change
- which workflows, APIs, or docs are touched

### Non-Negotiables

At minimum, every phase must preserve:

- service-layer-only transactional writes
- append-only ledger
- `Decimal`-only finance and inventory logic
- `farm_id` isolation
- unified truth chain:
  - `CropPlan -> DailyLog -> Activity -> Smart Card Stack -> Control -> Variance -> Ledger`
- `SIMPLE` as control surface, not ERP authoring
- mode-aware route and workflow enforcement

### Acceptance

Every phase must define:

- `code anchor`
- `test anchor`
- `gate anchor`
- `runtime/evidence anchor`

If any required runtime or gate proof is unavailable, the phase is `BLOCKED`, not `PASS`.

## Reject Conditions

A future phase proposal must be rejected immediately if it:

- treats `AGENTS.md` as higher authority than the `PRD`
- inverts manifest versus precedence responsibilities
- uses historical reports as live score authority
- proposes a change that breaks a declared non-negotiable
- proposes a `SIMPLE` finance authoring leak
- splits truth away from the canonical chain
- lacks explicit acceptance evidence

## Default Evidence Rule

Before any claim of readiness, completion, or restored `100/100`, the phase must be tied back to current canonical evidence.

At minimum, the planner must check whether the phase requires re-running:

- `python backend/manage.py verify_release_gate_v21`
- `python backend/manage.py verify_axis_complete_v21`

If the phase changes code, doctrine, or evidence-relevant behavior and a renewed readiness claim is made, canonical re-verification is mandatory.

## Recommended Working Style

Future phases should be described as:

- `AGENTS-driven`
- `manifest-resolved`
- `evidence-gated`

This is the default operating style for post-freeze work in V21.
