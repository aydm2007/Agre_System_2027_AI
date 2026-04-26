# Project Guardrails (AgriAsset Yemen)

## 1) Source of Truth
- Runtime policy source: `AGENTS.md`
- Primary execution skill: `.agent/skills/agri_guardian/SKILL.md`
- Data truth: production schema + Django migrations + latest SQL dump
- If ORM/schema conflict exists, resolve explicitly and document the decision

## 2) Tenant Isolation (Independent Farms)
- Every business mutation is farm-scoped
- `farm_id` (or strict traceable farm relation) is mandatory for transactional rows
- No cross-farm data access by default
- Cross-farm reports are read-only and explicitly authorized

## 3) No-IoT / Manual-First Rules
- No sensor-driven truth path in operations
- Manual supervisor input is the only accepted field evidence
- Outlier values must require supervisor note or approval
- Fuel inventory logs must use manual dipstick or mechanical counter inputs only
- Daily logs must reject telemetry-like payloads in observation data

## 4) Financial Integrity
- Ledger rows are immutable: no update/delete corrections
- Corrections are reversal entries only
- Costing and financial mutations must use `transaction.atomic()` and locking where needed
- Never swallow financial/database exceptions silently
- Zakat liabilities must be recognized at harvest using 5% (irrigated) or 10% (rain-fed) rules
- Sales confirmation must recognize revenue (`ACCOUNT_SALES_REVENUE`) before any sector remittance or payable transfer
- Depreciation ledger entries must use dynamic asset or system default currency (no hardcoded currency)

## 5) Decimal and Daily-Rate Law
- Use `Decimal` for money and quantities in mutation paths
- No `float` conversions in finance/inventory mutation logic
- Labor costing is Daily Rate (Surra), not hourly fallback
- Official staff cannot carry Surra shift rates; casual staff cannot carry base salary
- Rounding policy must be explicit and deterministic
- Planning and budget fields use `Decimal(19,4)` precision

## 6) Weak-Network Idempotency
- `X-Idempotency-Key` is mandatory for financial and inventory mutations
- Missing key => reject request (`400`)
- Duplicate key => deterministic non-destructive response
- Client retry must not create duplicate financial/stock effects
- Daily log submissions must replay cached responses when an idempotency key is reused

## 7) Variance and Control
- Track planned vs actual for quantity, cost, yield, and schedule
- Define warning/critical thresholds
- Critical variance requires approval trail
- No silent posting beyond critical thresholds
- Reporting aggregations must exclude soft-deleted rows to preserve forensic accuracy

## 8) Period Control
- Financial periods support open / soft-close / hard-close per farm
- Hard-closed period blocks new mutations
- Post-close corrections use reversal in open period with audit reference

## 9) SQL Hygiene and Forensics
- Detect zombie tables and ghost triggers after migration/release
- Validate managed/unmanaged model alignment to schema
- Keep RLS checks mandatory for tenant-sensitive tables

## 10) Release Gate (Must Pass)
- No mutation endpoint without idempotency enforcement
- No float-based finance/inventory mutation path
- No unresolved critical variance without approval trail
- No unresolved zombie/ghost schema findings
- Tenant isolation checks pass
