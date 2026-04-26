# Reference Layer Audit (Post-Closure)

## Current strict verdict
- **Canonical code + gates:** `100/100`
- **Latest score authority:** `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json`
- **Current command truth:** `overall_status=PASS` and `axis_overall_status=PASS`

This audit is no longer a pre-closure pack assessment. It records the active post-closure state of
the reference layer after the reporting contract, custody/offline doctrine, and deterministic
Playwright startup contract were aligned with the live canonical evidence.

## What is now aligned

### Product and execution truth
- `PRD V21` remains the product and acceptance truth.
- Root `AGENTS.md` remains the execution and evidence protocol.
- `REFERENCE_MANIFEST_V21.yaml` remains the loading map, not the override authority.
- Canonical skills remain execution lenses only and do not override `PRD` or `AGENTS.md`.

### Daily execution and dual-mode doctrine
- `SIMPLE` remains a technical control surface, not a diluted ERP authoring surface.
- `STRICT` remains the governed ERP surface over the same truth chain.
- `DailyLog` stays stack-first and read-side-first through `smart_card_stack`.
- Supervisor custody, offline replay, and waste separation are now reflected in active doctrine.

### Reporting doctrine and public contract
- `advanced-report` direct `GET` without explicit `section_scope` is now treated as a conservative,
  usable contract returning `summary + details`.
- Explicit `section_scope` enables sectional optimization only when sent intentionally by the caller.
- `Reports Hub` documentation now distinguishes the legacy conservative helper from the modern
  sectional async loader.

### Runtime and browser-proof doctrine
- Windows/browser verification now depends on deterministic backend startup:
  - preload PostgreSQL environment through `scripts/windows/Resolve-BackendDbEnv.ps1`
  - run `migrate --noinput`
  - then start Django `runserver`
- Browser proofs are therefore no longer interpreted against a stale local schema state.

## Remaining non-blocking improvement areas

These items are improvement opportunities, not blockers to `100/100` canonical closure:

- richer machine-readable reference metadata for skill status and lifecycle
- stronger separation between public docs, historical docs, and narrative architecture notes
- eventual OpenAPI-style formalization of reporting wire contracts
- continued reduction of historical examples that still use old non-`/api/v1/` paths

## Interpretation rule

- A reference file is compliant only when it does not outclaim or underclaim the latest canonical
  evidence.
- A historical or architecture note must be marked clearly when it is not a live contract source.
- If future code changes alter the reporting, custody, offline, or verification startup contracts,
  this file must be updated in the same change set.
