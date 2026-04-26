> [!IMPORTANT]
> Historical handoff only. This file is dated context and not the live score authority.
> Live authority:
> - `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json`
> - `docs/evidence/closure/latest/verify_release_gate_v21/summary.json`

# Release Handoff - 2026-03-27

## Executive Status
- Release baseline: `Gold Freeze candidate`
- Product compliance status: `PASS/PASS`
- New-tenant UAT status: `PASS`
- Release tag target: `gold-freeze-2026-03-27`
- Release commit: `resolved by the tag target for this baseline`

## Canonical Evidence
- `verify_axis_complete_v21`: `overall_status=PASS`, `axis_overall_status=PASS`
- `verify_release_gate_v21`: `overall_status=PASS`
- `Khameesiya UAT`: `overall_status=PASS`, `strict_summary_score=100.0`

## Verified Commands
- `python backend/manage.py run_khameesiya_uat --artifact-root docs/evidence/uat/khameesiya/latest`
- `python scripts/verification/verify_release_hygiene.py`
- `python backend/manage.py verify_release_gate_v21`
- `python backend/manage.py verify_axis_complete_v21`

## Evidence Paths
- `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json`
- `docs/evidence/closure/latest/verify_release_gate_v21/summary.json`
- `docs/evidence/uat/khameesiya/latest/summary.json`
- `docs/evidence/uat/khameesiya/latest/summary.md`
- `docs/evidence/uat/khameesiya/latest/before_report.json`

## Included Baseline Changes
- bootstrap and release-hygiene improvements already present in the active baseline
- Khameesiya dual-mode UAT harness and Playwright tenant proof
- service-layer compatibility fixes for costing currency fallback and governed receipt/deposit tracing
- canonical latest evidence summaries refreshed from the successful verification runs

## Environment Contract
- database engine: PostgreSQL only
- release authority: latest canonical closure summaries under `docs/evidence/closure/latest/`
- supporting UAT authority: `docs/evidence/uat/khameesiya/latest/`
- mode contract:
  - `SIMPLE` = posture/control surface only
  - `STRICT` = governed ERP over the same truth chain

## Rollback Path
- if a post-freeze verification fails before deployment, discard the candidate tag and re-run the canonical gates after remediation
- if deployment fails after tag publication, roll back to the previous approved release tag/image and restore the database only when forward-only recovery is not viable
- any future `BLOCKED` or `FAIL` in canonical closure evidence voids the release claim until re-verified

## Blocker Policy
- any active reference contradiction blocks release
- any dirty worktree at packaging time blocks release
- any mismatch between handoff prose and canonical summaries blocks release
- any new-tenant UAT regression in `docs/evidence/uat/khameesiya/latest/summary.json` blocks the current Gold Freeze baseline

## Residual Note
- this handoff records a successful freeze candidate for the dated baseline only
- the live project score must always be read from the latest canonical summaries, not from this dated handoff
