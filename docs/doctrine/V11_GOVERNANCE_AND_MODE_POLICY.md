# V11 Governance and Mode Policy

## 1. Core Position
- `SIMPLE` is a technical agricultural control system: plans, daily execution, variance visibility, readiness posture, and summarized control posture only.
- `STRICT` is the full governed ERP: approvals, treasury trace, receipts/deposit, supplier settlement, fixed assets, fuel reconciliation, contract settlement lifecycle, and governed evidence retention.
- Both modes share the same source-of-truth chain and backend posting logic.

## 2. Mode Boundary Rules
### SIMPLE
- field and agronomy teams operate daily execution, plans, materials, and control cards
- users see readiness, delay, anomaly, and burn-rate style control posture
- users do **not** receive the full chain of finance authoring and sector final approval UX by default
- contract operations show status, expected share/rent, touring state, and risk posture only
- operational attachments may be allowed, but authoritative final finance-evidence handling remains a strict concern

### STRICT
- exposes the complete governed ERP surface
- applies multi-step sector approvals where policy requires them
- exposes settlement, treasury, reconciliation, and close evidence
- enforces evidence classification, archive, retention, and purge rules

## 3. Farm-Size Governance
### SMALL
- local accountant may act as chief accountant and acting farm finance manager only when `single_finance_officer_allowed=true`
- local approval thresholds must exist
- weekly remote sector review is mandatory
- hard-close remains sector-owned

### MEDIUM / LARGE
- a dedicated `المدير المالي للمزرعة` is required
- farm accountant, chief accountant, and farm finance manager should be distinct by policy
- sector chain reviews and escalates rather than replacing daily farm work

## 4. Sector Chain
1. محاسب القطاع
2. مراجع القطاع
3. رئيس حسابات القطاع
4. المدير المالي لقطاع المزارع
5. مدير القطاع (business/executive final approval when policy requires)

## 5. Contract Operations Position
- Contracts are not technical crop execution.
- Touring is assessment-only and sits on harvest/production truth.
- Settlement, receipt trace, and reconciliation are `STRICT` surfaces.
- `SIMPLE` exposes contract posture and risk; `STRICT` exposes settlement detail.

## 6. Attachment Lifecycle Position
- `transient`: TTL purge/archive candidate
- `operational`: routine operational evidence
- `financial_record`: authoritative evidence retained and archived, not quickly deleted
- `legal_hold`: no expiry until formal release

## 7. Release Implication
A change is incomplete if it updates code but not:
- AGENTS/skills
- doctrine
- release evidence or blocker note
- PRD baseline when the functional contract changes
