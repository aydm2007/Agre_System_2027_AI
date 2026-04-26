# AgriAsset V21 Comprehensive Documentation Gateway

> Reference class: historical/public compatibility gateway.
> This file is retained for broad orientation and navigation. It is not a higher-order canonical
> source than `PRD V21`, `AGENTS.md`, doctrine, or the latest canonical evidence under
> `docs/evidence/closure/latest/`.
>
> Important:
> - older large-form compendium content previously kept here used legacy naming and older API
>   examples
> - use the linked canonical and public guides below for current contracts
> - historical narrative remains traceability context only

## Use these current sources first
- Product baseline: `docs/prd/AGRIASSET_V21_MASTER_PRD_AR.md`
- Execution protocol: `AGENTS.md`
- Reference precedence: `docs/reference/REFERENCE_PRECEDENCE_AND_OVERRIDE_V21.md`
- Reference manifest: `docs/reference/REFERENCE_MANIFEST_V21.yaml`
- Runtime checklist: `docs/reference/RUNTIME_PROOF_CHECKLIST_V21.md`
- Public API guide: `docs/API_REFERENCE.md`
- Public system overview: `docs/system_overview.md`
- Operational runbook: `docs/RUNBOOK.md`
- Deployment guide: `docs/DEPLOYMENT.md`

## Current documentation map

### Canonical execution and governance
- `AGENTS.md`
- `docs/reference/*`
- `docs/doctrine/*`
- `docs/prd/AGRIASSET_V21_MASTER_PRD_AR.md`

### Public operational and engineering guides
- `docs/system_overview.md`
- `docs/API_REFERENCE.md`
- `docs/RUNBOOK.md`
- `docs/DEPLOYMENT.md`
- `docs/backend_api_overview.md`

### Historical or dated reports
- `docs/reports/*`
- older PRD and doctrine versions outside the active V21 baseline
- dated handoff and closure notes that explicitly defer to latest canonical evidence

## Path policy reminder
- infrastructure endpoints live under `/api/`
- business routers live under `/api/v1/`
- do not infer live API truth from older `/api/` examples in historical material

## Score authority reminder
Any live `100/100` claim is valid only when the latest:
- `docs/evidence/closure/latest/verify_static_v21/summary.json`
- `docs/evidence/closure/latest/verify_release_gate_v21/summary.json`
- `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json`

remain green, with `verify_axis_complete_v21` reporting both:
- `overall_status=PASS`
- `axis_overall_status=PASS`
