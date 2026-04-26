# EVIDENCE SUMMARY V21

This file is a human-readable index only. It is not authoritative for score claims.

## Authoritative Evidence Sources

Use the latest generated suite summaries under `docs/evidence/closure/latest/`:

| Canonical gate | Authoritative summary |
|---|---|
| `verify_static_v21` | `docs/evidence/closure/latest/verify_static_v21/summary.json` |
| `verify_release_gate_v21` | `docs/evidence/closure/latest/verify_release_gate_v21/summary.json` |
| `verify_axis_complete_v21` | `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json` |

## Scoring Rule

- `100/100` is valid only when the latest `verify_axis_complete_v21/summary.json` reports both `overall_status=PASS` and `axis_overall_status=PASS`.
- Any `FAIL` or `BLOCKED` state in the latest canonical summary overrides older markdown summaries, screenshots, or manual notes.
- This file must not embed stale `PASS` claims that disagree with the latest generated suite summary.

## Interpretation Notes

- Runtime outbox readiness must be derived from the latest filtered readiness commands, not from historical console snippets.
- Playwright evidence is authoritative only when the current run completed against an isolated writable artifact root.
- Historical closure packs remain useful for traceability, but they do not overrule the latest canonical summaries.
