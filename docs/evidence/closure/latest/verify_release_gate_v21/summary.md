# V21 Release Gate Verification

- command: `verify_release_gate_v21`
- generated_at: `2026-04-25T01:31:03.595648-07:00`
- overall_status: `FAIL`
- suite_dir: `C:\tools\workspace\AgriAsset_v445\docs\evidence\closure\20260425_012907\verify_release_gate_v21`
- latest_dir: `C:\tools\workspace\AgriAsset_v445\docs\evidence\closure\latest\verify_release_gate_v21`

## Step Summary

| Group | Step | Status | Exit |
|---|---|---|---:|
| `static` | `Bootstrap/runtime contract` | `PASS` | `0` |
| `static` | `PostgreSQL foundation contract` | `PASS` | `0` |
| `static` | `Bare exception scan` | `PASS` | `0` |
| `static` | `Docx traceability coverage` | `PASS` | `0` |
| `static` | `Release hygiene static contract` | `PASS` | `0` |
| `static` | `Decimal mutation guard` | `PASS` | `0` |
| `static` | `Idempotency action contract` | `PASS` | `0` |
| `static` | `Farm scope guard contract` | `PASS` | `0` |
| `static` | `Service-layer write contract` | `PASS` | `0` |
| `static` | `Compliance docs contract` | `PASS` | `0` |
| `static` | `XLSX integrity gate` | `PASS` | `0` |
| `static` | `Float guard strict scan` | `PASS` | `0` |
| `backend_tests` | `Backend smart-card and mode tests` | `FAIL` | `1` |
| `backend_tests` | `Backend approval and reopen tests` | `FAIL` | `1` |
| `backend_tests` | `Backend attachment and runtime tests` | `FAIL` | `1` |
| `backend_tests` | `Backend supplier settlement and mode policy tests` | `FAIL` | `1` |
| `backend_tests` | `Backend contract, assets, fuel, and petty-cash tests` | `FAIL` | `1` |
| `frontend` | `Frontend lint` | `PASS` | `0` |
| `frontend` | `Frontend focused Vitest suites` | `PASS` | `0` |
| `frontend` | `Frontend build` | `PASS` | `0` |
| `runtime` | `Django system checks` | `PASS` | `0` |
| `runtime` | `Seed runtime governance evidence` | `FAIL` | `1` |
| `runtime` | `Django migrations status` | `PASS` | `0` |
| `runtime` | `Django migration plan` | `PASS` | `0` |
| `runtime` | `Runtime probe V21` | `PASS` | `0` |
| `runtime` | `Release readiness snapshot` | `PASS` | `0` |
| `runtime` | `Attachment scan` | `PASS` | `0` |
| `runtime` | `Due remote reviews` | `PASS` | `0` |
| `runtime` | `Persistent outbox dispatch` | `PASS` | `0` |
| `runtime` | `Persistent outbox retry dead letters` | `PASS` | `0` |
| `runtime` | `Persistent outbox purge dry-run` | `PASS` | `0` |

## Copied Artifacts

- `C:\tools\workspace\AgriAsset_v445\backend\release_readiness_snapshot.json`
- `C:\tools\workspace\AgriAsset_v445\backend\release_readiness_snapshot.md`
- `C:\tools\workspace\AgriAsset_v445\backend\scripts\release_gate_float_check.txt`
