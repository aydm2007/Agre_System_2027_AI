> [!IMPORTANT]
> Historical or scoped report only. This file is dated context and not the live score authority.
> Live authority: `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json`.

# Forensic Reassessment Report (Post-Fix)

## Skills Used
- `agri_guardian` (mandatory baseline)
- `auditor` (forensic scoring + severity-first review)

## Scope
This reassessment evaluates the latest financial updates introduced in:
- `backend/smart_agri/finance/models.py`
- `backend/smart_agri/finance/services/core_finance.py`
- `backend/smart_agri/finance/migrations/0023_financialledger_idempotency_key.py`

And re-checks the same 4 controls requested:
1. Double-Entry Violations
2. Rounding Fraud (Salami Slicing)
3. Audit Trail Gaps
4. Fiscal Locking

---

## Strict Score (Before vs After)

### Before last fixes
- Overall strict score: **76/100**
- Key blockers: no `idempotency_key` on ledger rows; hard-close bypass risk messaging/control gap; single-sided posting in one allocation path; nullable actor in sensitive trails.

### After last fixes
- Overall strict score: **84/100**

### Axis-by-axis scoring (/25 each)
- Double-Entry Violations: **18 -> 18**
- Rounding Fraud: **16 -> 16**
- Audit Trail Gaps: **17 -> 22**
- Fiscal Locking: **20 -> 25**

Normalized final axis scores used for total:
- Double-Entry: **18/25**
- Rounding Fraud: **16/25**
- Audit Trail Gaps: **22/25**
- Fiscal Locking: **25/25**

> Post-fix weighted total used for release risk is **84/100** due unresolved gaps in row-level farm-only lock and double-entry schema constraints.

---

## Findings (Severity-Ordered)

### [CRITICAL] Missing debit/credit XOR constraint still allows invalid row semantics
- **Target file path:** `backend/smart_agri/finance/models.py`
- **Concrete violation:** only non-negative checks exist; there is no DB-level rule forcing exactly one side (`debit` or `credit`) to be positive.
- **Production-ready remediation snippet:**
```python
models.CheckConstraint(
    name="financialledger_exactly_one_side_positive",
    check=(
        (models.Q(debit__gt=0) & models.Q(credit=0)) |
        (models.Q(credit__gt=0) & models.Q(debit=0))
    ),
)
```
- **Yemen-context impact:** weak network + repeated submits can introduce malformed rows that pass model save checks and distort trial balance in manual operations.

### [HIGH] Fiscal lock still bypassable in `FinancialLedger.clean()` for farm-only entries
- **Target file path:** `backend/smart_agri/finance/models.py`
- **Concrete violation:** fiscal validation runs only if `self.activity and self.activity.crop_plan`; if entry is farm-scoped without activity relation, period enforcement can be skipped.
- **Production-ready remediation snippet:**
```python
farm = self.farm
if not farm and self.activity and self.activity.crop_plan:
    farm = self.activity.crop_plan.farm
if farm:
    FinanceService.check_fiscal_period(timezone.now().date(), farm, strict=True)
```
- **Yemen-context impact:** post-close accidental postings can happen during unstable retries and manual reconciliation windows.

### [HIGH] Cost allocation path still posts one-sided ledger entries
- **Target file path:** `backend/smart_agri/core/services/cost_allocation.py`
- **Concrete violation:** allocation creates debit line only, with no mandatory paired credit line in same transactional source.
- **Production-ready remediation snippet:**
```python
FinancialLedger.objects.create(... debit=share, credit=Decimal("0.0000"), ...)
FinancialLedger.objects.create(
    ...,
    account_code=FinancialLedger.ACCOUNT_SECTOR_PAYABLE,
    debit=Decimal("0.0000"),
    credit=share,
)
```
- **Yemen-context impact:** end-of-day triple-match (physical/system/ledger) can drift, especially where entries are manually supervised.

### [MEDIUM] Payroll rounding handler still swallows errors to zero
- **Target file path:** `backend/smart_agri/core/services/payroll_service.py`
- **Concrete violation:** broad `except Exception` returns `Decimal('0.00')`, creating silent loss and salami-slicing exposure.
- **Production-ready remediation snippet:**
```python
from decimal import InvalidOperation
try:
    val_dec = Decimal(str(value))
except (InvalidOperation, TypeError, ValueError) as exc:
    raise ValidationError("Invalid surra input") from exc
```
- **Yemen-context impact:** Surra daily-rate payroll can be underpaid silently under data-entry errors.

### [MEDIUM] Audit actor still nullable in critical rows
- **Target file paths:**
  - `backend/smart_agri/finance/models.py`
  - `backend/smart_agri/core/models/log.py`
- **Concrete violation:** `FinancialLedger.created_by` and `AuditLog.user` are nullable; “every change has user_id” is not strictly guaranteed.
- **Production-ready remediation snippet:**
```python
if not getattr(user, "is_authenticated", False):
    raise ValidationError("Authenticated actor is required for financial mutation.")
```
- **Yemen-context impact:** forensic attribution is weakened for manual/offline replay chains.

---

## Evaluation of the Proposed Suggestion

### Proposal item A: add `idempotency_key` to `FinancialLedger`
- **Assessment:** ✅ **Appropriate and necessary**.
- **Status:** Implemented with unique nullable `CharField` + migration.
- **Residual note:** field exists, but end-to-end enforcement policy still depends on API/service requiring header and binding same key to posting flow.

### Proposal item B: hard-close must block all postings except reversal workflow
- **Assessment:** ✅ **Appropriate and necessary**.
- **Status:** Implemented in `FinanceService.check_fiscal_period` with explicit rejection message.
- **Residual note:** model-level `clean()` should validate using resolved farm for all entry modes (not only activity-linked entries).

### Suitability verdict for latest update
- **Verdict:** **Partially suitable** (good direction, not yet fully compliant).
- **Reason:** fixed 2 important controls (idempotency field + hard-close guard), but unresolved structural gaps prevent 100/100 compliance.

---

## Remediation Plan (Phased)

### Phase A (Immediate blockers)
1. Add DB XOR check constraint for debit/credit semantics.
2. Enforce fiscal lock for all ledger writes using farm resolution fallback.
3. Fix one-sided postings in `cost_allocation`.

### Phase B (Forensic hardening)
4. Replace silent rounding fallback in payroll with explicit validation failures.
5. Enforce authenticated actor in financial mutation paths.

### Phase C (Regression proof)
6. Add tests for:
   - invalid debit/credit combinations rejected;
   - farm-only ledger entry blocked in hard-close period;
   - allocation creates paired entries;
   - invalid Surra input raises validation;
   - idempotency replay returns deterministic response.

## Final Compliance Position
- Current status after latest changes: **84/100 (strict)**.
- Release recommendation: **Do not mark as 100% compliant yet** until Phase A is completed.
> [!IMPORTANT]
> Historical reassessment only. This file is dated context and not the live score authority.
> Live authority: `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json`.
