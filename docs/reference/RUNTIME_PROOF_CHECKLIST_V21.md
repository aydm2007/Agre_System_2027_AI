# Runtime Proof Checklist (V21)

> Checklist only. Actual status must be read from `docs/evidence/closure/latest/<command>/summary.json`. Any command not actually executed is `BLOCKED`, not `PASS`.

## Authority

- `100/100` requires the latest `verify_axis_complete_v21/summary.json` to report both `overall_status=PASS` and `axis_overall_status=PASS`.
- If the latest canonical summary is `FAIL` or `BLOCKED`, this checklist cannot be used to claim completion.
- Historical markdown notes never outrank the latest generated summary.

## Canonical Commands

### Backend / Django

| Command | Expected outcome | Authoritative evidence |
|---|---|---|
| `python backend/manage.py check --deploy` | PASS | `docs/evidence/closure/latest/verify_release_gate_v21/summary.json` |
| `python backend/manage.py showmigrations --plan` | PASS / reviewed | `docs/evidence/closure/latest/verify_release_gate_v21/summary.json` |
| `python backend/manage.py migrate --plan` | PASS / reviewed | `docs/evidence/closure/latest/verify_release_gate_v21/summary.json` |
| `python backend/manage.py runtime_probe_v21` | PASS | `docs/evidence/closure/latest/verify_release_gate_v21/summary.json` |
| `python backend/manage.py release_readiness_snapshot` | PASS | `docs/evidence/closure/latest/verify_release_gate_v21/summary.json` |
| `python backend/manage.py scan_pending_attachments` | PASS / reviewed | `docs/evidence/closure/latest/verify_release_gate_v21/summary.json` |
| `python backend/manage.py report_due_remote_reviews` | PASS / reviewed | `docs/evidence/closure/latest/verify_release_gate_v21/summary.json` |
| `python backend/manage.py dispatch_outbox --batch-size 10 --metadata-flag seed_runtime_governance` | PASS / reviewed | `docs/evidence/closure/latest/verify_release_gate_v21/summary.json` |
| `python backend/manage.py retry_dead_letters --limit 10 --metadata-flag seed_runtime_governance` | PASS / reviewed | `docs/evidence/closure/latest/verify_release_gate_v21/summary.json` |
| `python backend/manage.py purge_dispatched_outbox --dry-run --metadata-flag seed_runtime_governance` | PASS / reviewed | `docs/evidence/closure/latest/verify_release_gate_v21/summary.json` |
| `python backend/manage.py run_governance_maintenance_cycle --dry-run` | PASS / reviewed | `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json` |

### Frontend

| Command | Expected outcome | Authoritative evidence |
|---|---|---|
| `npm --prefix frontend run lint` | PASS | `docs/evidence/closure/latest/verify_release_gate_v21/summary.json` |
| `npm --prefix frontend run test:ci` | PASS | `docs/evidence/closure/latest/verify_release_gate_v21/summary.json` |
| `npm --prefix frontend run build` | PASS | `docs/evidence/closure/latest/verify_release_gate_v21/summary.json` |
| `npx --prefix frontend playwright test ... --reporter=line` | PASS | `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json` |

### Release Gates

| Command | Expected outcome | Authoritative evidence |
|---|---|---|
| `python backend/manage.py verify_static_v21` | PASS | `docs/evidence/closure/latest/verify_static_v21/summary.json` |
| `python backend/manage.py verify_release_gate_v21` | PASS | `docs/evidence/closure/latest/verify_release_gate_v21/summary.json` |
| `python backend/manage.py run_closure_evidence_v21` | PASS | `docs/evidence/closure/latest/run_closure_evidence_v21/summary.json` |
| `python backend/manage.py verify_axis_complete_v21` | PASS | `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json` |

## Operational Notes

- Playwright runs in canonical gates must use an isolated writable artifact root via `PLAYWRIGHT_ARTIFACT_ROOT`; otherwise write-lock failures are `BLOCKED`.
- Outbox readiness evidence must be scoped to seeded governance rows via `metadata.seed_runtime_governance=true` so closure runs remain deterministic.
- Supplemental browser bundles, such as expanded SIMPLE readiness packs, may be attached as supporting evidence. They do not override the authority of the latest canonical summaries under `docs/evidence/closure/latest/`.
- Import/export platform proofs may be attached as supplemental readiness evidence for the first-wave `XLSX/JSON` platform. They do not replace canonical release-gate authority.
- Business-facing import/export files in the first wave must be validated as Arabic/RTL `XLSX`; `JSON` remains optional and technical.
- Planning-import platform proofs may be attached as supplemental readiness evidence when `planning_master_schedule`, `planning_crop_plan_structure`, and strict-only `planning_crop_plan_budget` are exercised through backend preview/apply.
- Wave 2 / Wave 3 report-catalog proofs may be attached as supplemental readiness evidence when the unified registry, history panels, and module-local export centers expand. They remain supplemental unless promoted by an updated canonical gate pack.
- SIMPLE finance read-only closure should include a deploy-smoke probe for `GET /api/v1/shadow-ledger/?farm=<simple_farm>` and `GET /api/v1/shadow-ledger/summary/?farm=<simple_farm>`; a frontend deployment that points to a missing shadow-ledger backend route is a deployment-integration blocker, not a business-permission blocker.
- Any runtime stack blocker must be recorded in the latest summary with its impact on final score.

## Scoring rule

- **95+** requires most of this checklist green with no critical blocker.
- **98** requires real `PASS` across runtime probe + release gate + key tests + focused runtime/browser proof on the governed workflows.
- **100** requires the active reference layer to stay aligned with the runtime evidence, including attachment forensics scenarios, self-contained outbox readiness evidence, and a green `verify_axis_complete_v21` run with all 18 axes `PASS`.
- Any `BLOCKED` item must explain whether it is environmental or project-derived and state its impact on the final score.
