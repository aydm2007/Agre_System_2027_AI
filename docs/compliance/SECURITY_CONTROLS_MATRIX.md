# Security Controls Matrix (ISO 27001 / NIST CSF / COBIT)

## Mapping Table
| control_id | control_objective | ISO_27001_family | NIST_CSF | COBIT_process | implemented_by | evidence_path | test_command | residual_risk |
|---|---|---|---|---|---|---|---|---|
| C-01 | Strong access control and least privilege | A.5, A.8 | PR.AC | DSS05 | RBAC + farm-scoped auth + RLS | `AGENTS.md`, `docs/architecture/06_rls_policies.md` | `python scripts/check_farm_scope_guards.py` | Low |
| C-02 | Transaction integrity under retries | A.8, A.12 | PR.DS | DSS06 | Idempotency V2 for financial mutations | `AGENTS.md`, `backend/smart_agri/core/services/idempotency.py` | `python scripts/check_idempotency_actions.py` | Low |
| C-03 | Schema integrity and drift prevention | A.8, A.12 | DE.CM | BAI03 | Zombie/Ghost checks + migration parity | `scripts/verification/detect_zombies.py` | `python scripts/verification/detect_zombies.py` | Medium |
| C-04 | Financial data immutability | A.8 | PR.DS | DSS06 | Append-only ledger + reversal-only correction | `AGENTS.md`, `docs/FINANCE_TREASURY.md` | `python backend/scripts/check_solar_depreciation_logic.py` | Low |
| C-05 | Availability and recovery | A.5, A.17 | RC.RP | DSS04 | DR runbook + monthly drill | `docs/compliance/DR_BCP_RUNBOOK.md`, `docs/reports/DR_DRILL_*.md` | `python scripts/verification/check_restore_drill_evidence.py` | Medium |
| C-06 | Data governance and privacy | A.5, A.8 | PR.DS | APO14 | Classification, retention, sanitized export policy | `docs/compliance/DATA_GOVERNANCE_STANDARD.md` | `python scripts/verification/check_compliance_docs.py` | Medium |
| C-07 | Release governance and change control | A.5, A.8 | ID.GV | BAI06 | Evidence-based CI gate + emergency change protocol | `docs/compliance/RELEASE_GOVERNANCE_STANDARD.md` | `python scripts/verification/check_compliance_docs.py` | Low |

## Control Ownership
- Security Admin: C-01, C-06
- Backend Lead: C-02, C-04
- Platform Lead: C-03, C-05
- Engineering Manager: C-07

## External Gate Note
This matrix provides internal audit traceability and control mapping readiness. Formal external certification (ISO/SOC) remains an external governance decision.
