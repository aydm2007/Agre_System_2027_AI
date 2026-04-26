# Post-Closure Residual Standards Gaps

## Explicit verdict
`100/100` canonical closure has been achieved for the active V21 evidence gate.

This file no longer tracks blockers to reach `100/100`. It tracks **post-closure residual
improvement areas** that matter for long-term enterprise quality, public contract discipline, and
maintainability.

## Residual global-standard improvement areas

### 1) API governance maturity
- Promote more public contracts to explicit OpenAPI-style documentation.
- Keep conservative `direct GET` versus sectional async reporting semantics documented and tested
  together.
- Ensure public examples stay synchronized with `farm|farm_id`, `location|location_id`,
  `season|season_id`, and `section_scope` support.

### 2) Documentation lifecycle discipline
- Mark historical/non-authoritative documents explicitly when they are retained for traceability.
- Prevent public examples from drifting behind canonical `PRD + AGENTS + doctrine + live evidence`.
- Continue reducing outdated examples that use older API roots or older contract wording.

### 3) Contract testing maturity
- Keep non-gated integration tests aligned with the current public contract so they do not silently
  teach an older behavior.
- Prefer regression tests that prove both:
  - conservative legacy compatibility
  - explicit optimized contract behavior

### 4) Deterministic browser/runtime verification
- Preserve hermetic browser startup semantics on Windows and weak-network environments.
- Keep Playwright backend startup environment-aware and schema-aware.
- Avoid any future browser proof that assumes a developer-local migrated database state.

### 5) Traceability quality
- Maintain `code + test + gate + evidence` anchors for any future reporting or smart-card contract
  change.
- Keep doctrine edits and workflow tests in the same change set where practical.

## Non-blocking interpretation

These are not active blockers to V21 closure. They become blockers only when:
- a future change breaks public contract alignment
- doctrine drifts behind code
- browser proofs stop being reproducible
- public docs begin to contradict canonical truth again
