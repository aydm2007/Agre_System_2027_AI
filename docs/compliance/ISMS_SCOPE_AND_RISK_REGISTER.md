# ISMS Scope and Risk Register

## Scope
- Backend services: Django/DRF (`backend/smart_agri`)
- Frontend services: React/Vite (`frontend/src`)
- Database: PostgreSQL (`localhost:5432` for local; managed DB in staged/prod)
- CI/CD: GitHub Actions (`.github/workflows`)
- Secrets and credentials: environment variables only; no secrets in git.
- Release artifacts and compliance evidence: `docs/reports/` and `frontend/.pw-results/`.

## Asset Inventory
| asset_id | asset_name | owner_role | criticality | confidentiality |
|---|---|---|---|---|
| A-01 | Financial Ledger data | Sector Finance Director | Critical | Restricted |
| A-02 | Inventory and stock movement data | Farm Manager | High | Confidential |
| A-03 | User auth tokens and session context | Security Admin | Critical | Restricted |
| A-04 | CI pipelines and release workflows | DevOps Lead | High | Internal |
| A-05 | Compliance evidence reports | Compliance Officer | High | Internal |

## Risk Register
| risk_id | control_family | scenario | likelihood(1-5) | impact(1-5) | score | mitigation | owner | acceptance_criteria | evidence |
|---|---|---|---:|---:|---:|---|---|---|---|
| R-01 | Access Control | Unauthorized access to financial APIs | 2 | 5 | 10 | RBAC + farm isolation + RLS + idempotency checks | Security Admin | No cross-farm leakage and no unauthorized hard-close paths | `scripts/check_farm_scope_guards.py`, RLS probes |
| R-02 | Data Integrity | Duplicate financial writes under weak network retries | 2 | 5 | 10 | Idempotency V2 Cache&Replay + atomic mutations | Backend Lead | Duplicate request never creates second write | `scripts/check_idempotency_actions.py` |
| R-03 | Availability | Service outage due to DB failure | 3 | 4 | 12 | DR runbook + monthly backup/restore drill + RTO/RPO targets | Platform Lead | Last monthly drill PASS with measured RTO/RPO | `docs/reports/DR_DRILL_*.md` |
| R-04 | Change Management | Unverified change reaches production | 2 | 4 | 8 | CI release gates + evidence-based merge block | Engineering Manager | Merge blocked when evidence or mandatory checks missing | `.github/workflows/nonfunctional-compliance-gate.yml` |
| R-05 | Privacy | Sensitive data leaked in debug dumps | 2 | 4 | 8 | Sanitized exports only + retention/classification standard | Compliance Officer | No raw sensitive dump in repository history | `DATA_GOVERNANCE_STANDARD.md` checklist |

## Risk Scoring Method
- score = likelihood x impact.
- score >= 12: immediate treatment and monthly review.
- score 8-11: active control and quarterly review.
- score <= 7: monitor.

## Review Cadence
- Monthly operational review of risks and controls.
- Immediate update after any incident or emergency change.
