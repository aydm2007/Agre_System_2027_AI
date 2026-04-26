# Data Governance Standard

## Data Classification
| level | description | examples | required_controls |
|---|---|---|---|
| Public | intended for public distribution | public product catalog metadata | integrity checks |
| Internal | internal operational data | crop plans, generic reports | authenticated access |
| Confidential | business-sensitive operational/financial data | budgets, expense approvals | RBAC + farm scope + audit logs |
| Restricted | highly sensitive data | auth tokens, personal identifiers, privileged security logs | strict least privilege + masked exports |

## Retention Schedule
| data_domain | minimum_retention | archival_policy | deletion_rule |
|---|---|---|---|
| Financial ledger and audit | 10 years | immutable archival snapshots | reversal-only corrections; no hard delete |
| Operational logs | 5 years | periodic archival | controlled purge after retention window |
| Auth/session logs | 1 year | secure rolling storage | auto-delete after retention policy |
| E2E/CI artifacts | 90 days | compressed archive when needed | auto-clean after TTL |

## PII and Sensitive Data Handling
- Collect only fields required for business/legal operations.
- Do not commit raw production dumps, tokens, or user secrets to git.
- Use sanitized exports for QA/training.
- Mask personal identifiers in shared evidence files.

## Pre-Release Data Checklist
- [ ] No sensitive dump files are tracked in repository.
- [ ] Evidence files do not expose credentials/tokens.
- [ ] Export examples are sanitized.
- [ ] Retention rules acknowledged for new data sources.

## Compliance Hooks
- `python scripts/verification/check_compliance_docs.py`
- `python scripts/verification/check_backup_freshness.py`
