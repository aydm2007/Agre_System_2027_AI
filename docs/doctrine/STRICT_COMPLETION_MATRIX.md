# Strict Completion Matrix

This matrix is the operational bridge between `AGENTS.md`, documentary cycles, SIMPLE/STRICT exposure, API surfaces, service-layer ownership, and verification evidence.

## Canonical Rules

- Every governed workflow must expose the same business truth in `SIMPLE` and `STRICT`.
- `SIMPLE` may hide finance detail, but must not bypass shadow accounting, audit, or variance generation.
- `STRICT` must preserve the same source truth while exposing approvals, settlements, treasury trace, and reconciliation posture.
- Mutations must be owned by services, never by API views directly.
- Documentary-cycle files in `Docx/` must be traceable to code through `DOCX_CODE_TRACEABILITY_MATRIX_V10.md`.

## Workflow Traceability Matrix

| Workflow | Documentary cycle | SIMPLE contract | STRICT contract | API surface | Service owner | Current verification evidence |
|---|---|---|---|---|---|---|
| Daily Execution Smart Card Stack | Crop plan -> daily log -> activity -> smart card stack -> control | execution + materials/labor/irrigation/machinery/fuel posture + variance + summarized cost posture | same operational truth + fuller approval/ledger visibility + governed financial trace | `core/api/viewsets/crop.py`, `core/services/daily_log_execution.py`, `frontend/src/components/daily-log/DailyLogSmartCard.jsx`, `frontend/src/pages/ServiceCards.jsx` | `daily_log_execution.py` | canonical stack contract + backend service-card tests + frontend DailyLog/ServiceCards renderer tests + stack-first fallback coverage |
| Petty Cash | request -> approval -> disbursement -> settlement | request state + due posture + exceptions | approval + disbursement + settlement + liability balancing | `finance/api_petty_cash.py` | `petty_cash_service.py` | idempotency gate pass; finance service-layer write gate pass |
| Receipts and Deposit | collection -> treasury -> deposit | posture + anomalies + summarized exposure | full treasury trace and deposit posture | `finance/api_treasury.py` and dashboards | `treasury_service.py` | idempotency gate pass; finance service-layer write gate pass |
| Supplier Settlement | payable review -> approval -> payment -> reconciliation | payable state + delay + posture | review + approval + payment + reconciliation trace | `finance/api_supplier_settlement.py` | `supplier_settlement_service.py` | finance service-layer write gate pass |
| Actual Expenses | expense request -> booking -> allocation | summarized expense posture | governed expense booking, allocation, and soft-delete | `finance/api_expenses.py` | `actual_expense_service.py` | finance service-layer write gate pass |
| Approval Governance | approval matrix -> request -> approve/reject | summarized routing posture | explicit authority and approval trace | `finance/api_approval.py` | `approval_service.py` | finance service-layer write gate pass |
| Worker Advances | salif issuance -> payroll deduction posture | worker outstanding posture | governed issuance + deduction readiness | `finance/api_advances.py` | `advances_service.py` | finance service-layer write gate pass |
| Fiscal Lifecycle | open -> soft-close -> hard-close | visibility only | governed lifecycle controls | `finance/api_fiscal.py` | `fiscal_governance_service.py`, `financial_integrity_service.py` | finance service-layer write gate pass |
| Manual Ledger Approval | pending manual entries -> maker-checker approval | hidden from non-finance surface | sector-finance approval of manual entries | `finance/api_ledger.py` | `ledger_approval_service.py` | finance service-layer write gate pass |
| Contract Operations | sharecropping / touring / rental posture | posture + expected share/rent + touring assessment state + summarized risk | settlement trace, rent/share receipt trace, reconciliation posture, and governed approval lane | dashboards + `contract_operations_service.py` | `contract_operations_service.py` | doctrine alignment + contract-operations dashboard tests + route-breach coverage for strict-only posting actions |
| Fixed Assets | asset register -> depreciation posture | tracking + health + summarized values | capitalization posture and governed visibility | `core/views/fixed_assets_dashboard.py`, `core/api/viewsets/farm.py` | `core/services/fixed_asset_workflow_service.py`, `core/services/fixed_asset_lifecycle_service.py` | seeded runtime snapshot + dedicated read-model service + governed capitalization/disposal API tests |
| Fuel Reconciliation | machine card -> expected vs actual fuel -> anomaly posture | anomalies + summarized risk | governed reconciliation posture | `core/views/fuel_reconciliation_dashboard.py` | `core/services/fuel_reconciliation_service.py`, `core/services/fuel_reconciliation_posting_service.py` | seeded runtime snapshot + dedicated read-model service + governed posting API tests |
| Attachments / Forensics | upload -> scan -> quarantine/archive/restore/purge | lightweight operational evidence where policy allows | class-aware intake, archive, legal-hold, restore, purge governance | attachment intake APIs + maintenance commands | attachment policy services + maintenance cycle | seeded runtime counts + scan/quarantine tests + attachment policy matrix scenarios |
| Outbox / Integration Hub | outbox enqueue -> dispatch -> retry/dead-letter -> purge dry-run | summarized delivery posture only | governed delivery trace and release readiness evidence | `integration_hub` runtime commands + readiness snapshot | persistent outbox services + `ReadinessEvidencePublisher` | self-contained readiness publisher profile + seeded success/retry/dead-letter counts + release-gate pass |
| Farm Membership Governance | farm roster -> role assignment -> managed removal | roster visibility + can-manage posture | governed create/update/delete for memberships | `accounts/api_membership.py` | `accounts/services.py::MembershipService` | accounts service-layer write gate pass |
| Governance and RACI | governance tier -> RACI template -> delegation -> permission template | summarized governance posture | governed approvals, delegation, and template ownership | `accounts/api_governance.py` | `accounts/services.py::GovernanceService` | accounts service-layer write gate pass |
| Auth Users and Groups | user roster -> permission/group assignment | roster visibility + self-scope | governed user/group lifecycle and strict-mode warnings | `accounts/api_auth.py` | `accounts/services.py::UserWriteService`, `GroupWriteService` | auth service-layer write gate pass |

## Verification Additions

Add these to release readiness when the runtime environment is available:

```bash
python scripts/verification/check_service_layer_writes.py
python scripts/verification/check_accounts_service_layer_writes.py
python scripts/verification/check_auth_service_layer_writes.py
python scripts/verification/check_bootstrap_contract.py
python scripts/verification/check_docx_traceability.py
python scripts/check_no_float_mutations.py
python scripts/check_idempotency_actions.py
python scripts/check_farm_scope_guards.py
python scripts/verification/check_no_bare_exceptions.py
```

## Role Gate Summary

- `رئيس حسابات المزرعة`: local accounting review, accounting-pack quality, and soft-close-readiness only.
- `المدير المالي للمزرعة`: local strict gate at the farm level where policy requires it.
- `رئيس حسابات القطاع`: accounting sign-off, reconciliation sign-off, and sector close-readiness gate.
- `المدير المالي لقطاع المزارع`: sector-final financial approval for governed thresholds, `strict_finance` final posting actions, and hard-close authority.
- Contract operations remain contract/economic workflows. Touring is assessment-only and must not generate technical agronomy execution.

## Remaining Runtime Evidence Needed for a provable 100/100

The repository now has deterministic frontend CI, stronger governed evidence for fixed assets and fuel reconciliation, and self-contained outbox readiness evidence through the `readiness_composite` publisher profile. A provable `100/100` claim still requires keeping these runtime and release checks green in the active verification run.
