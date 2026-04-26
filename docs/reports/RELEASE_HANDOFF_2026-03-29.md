> [!IMPORTANT]
> Historical handoff only. This file is dated context and not the live score authority.
> Live authority:
> - `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json`
> - `docs/evidence/closure/latest/verify_release_gate_v21/summary.json`

# Release Handoff - 2026-03-29

## Executive Status
- Release baseline: `Gold Freeze`
- Product compliance status: `PASS/PASS`
- Release tag target: `gold-freeze-2026-03-29`
- Release commit: `resolved by the tag target for this baseline`
- Freeze scope: `Mode Truth Unification + Fuel/Fixed-Assets posture hardening + SSE stream dedup in UI + frontend hygiene closure`

## Canonical Evidence
- `verify_release_gate_v21`: `overall_status=PASS`
  - `generated_at=2026-03-29T04:31:41.859817-07:00`
- `verify_axis_complete_v21`: `overall_status=PASS`, `axis_overall_status=PASS`
  - `generated_at=2026-03-29T04:37:36.812825-07:00`

## Verified Commands
- `npm --prefix frontend run lint`
- `npm --prefix frontend run build`
- `npm --prefix frontend run test -- src/auth/__tests__/modeAccess.test.js src/auth/__tests__/modeAccessExtended.test.js src/pages/__tests__/FuelReconciliationDashboard.test.jsx src/pages/__tests__/FixedAssetsDashboard.test.jsx --run`
- `npx playwright test tests/e2e/dual-mode-switch.spec.js tests/e2e/fuel-reconciliation.spec.js tests/e2e/fixed-assets.spec.js --reporter=line`
- `python scripts/verification/verify_release_hygiene.py`
- `python backend/manage.py verify_release_gate_v21`
- `python backend/manage.py verify_axis_complete_v21`

## Included Baseline Changes
- `SettingsContext` is the farm-scoped truth layer for mode-sensitive UI behavior
- `AuthContext.strictErpMode` remains bootstrap and auth context only
- `Fuel Reconciliation` and `Fixed Assets` preserve posture-first behavior in `SIMPLE` without flipping banners to `STRICT`
- `ModeGuard`, dashboard surfaces, approval surfaces, navigation, and farm carry-over now align on the same farm-scoped mode contract
- `LiveNotificationToast` now consumes the shared ops runtime stream instead of opening a duplicate SSE connection
- temporary helper scripts used during local repair are removed from the tracked baseline

## Evidence Paths
- `docs/evidence/closure/latest/verify_release_gate_v21/summary.json`
- `docs/evidence/closure/latest/verify_release_gate_v21/summary.md`
- `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json`
- `docs/evidence/closure/latest/verify_axis_complete_v21/summary.md`

## Environment Contract
- database engine: `PostgreSQL only`
- release authority: latest canonical closure summaries under `docs/evidence/closure/latest/`
- mode contract:
  - `SIMPLE` = technical agricultural control surface only
  - `STRICT` = governed ERP over the same truth chain
- truth chain remains:
  - `CropPlan -> DailyLog -> Activity -> Smart Card Stack -> Control -> Variance -> Ledger`

## Freeze Acceptance Conditions
- dirty worktree at packaging time blocks release
- any `FAIL` or `BLOCKED` in canonical gate evidence voids this freeze claim
- any mismatch between handoff prose and canonical summaries blocks release
- any later post-freeze change must re-run the canonical gate suite before inheriting this claim

## Rollback Path
- if a post-freeze verification fails before deployment, discard the candidate tag and re-run the canonical gates after remediation
- if deployment fails after tag publication, roll back to the previous approved release tag/image and restore the database only when forward-only recovery is not viable
- canonical score authority stays with `latest` evidence, not with this dated handoff

## Residual Note
- this handoff records a successful freeze candidate for the exact frozen tree only
- roadmap items after this baseline belong to post-100 enhancement work and must not be merged into the freeze claim implicitly
