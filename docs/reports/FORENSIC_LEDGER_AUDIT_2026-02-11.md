# Forensic Accountant & Systems Auditor Report

## Scope
- Module reviewed: financial posting and control paths around `FinancialLedger`.
- Evidence set:
  - `backend/smart_agri/finance/models.py`
  - `backend/smart_agri/finance/services/core_finance.py`
  - `backend/smart_agri/finance/services/financial_integrity_service.py`
  - `backend/smart_agri/core/services/cost_allocation.py`
  - `backend/smart_agri/core/services/payroll_service.py`
  - `backend/smart_agri/core/models/log.py`

## Executive Score (Strict)
- **Total: 76 / 100**

### Axis Scores
1. Double-Entry Integrity: **18/25**
2. Rounding Fraud Resistance: **16/25**
3. Audit Trail Completeness: **17/25**
4. Fiscal Locking Enforcement: **25/25**

> Normalized strict total after risk weighting: **76/100**.

## Findings (Ordered by Severity)

### 1) [CRITICAL] One-sided ledger constraint missing (permits invalid row semantics)
- **Target file**: `backend/smart_agri/finance/models.py`
- **Violation**: DB checks enforce only non-negative debit/credit, but do **not** enforce XOR behavior (`debit > 0, credit = 0` OR `credit > 0, debit = 0`). This allows rows with both sides positive or both zero.
- **Why this matters (Yemen context)**:
  - In weak/offline replay conditions, malformed rows can pass silently and distort trial balance reconciliation.
  - Manual-entry environments need hard DB-level guards to avoid operator and sync drift errors.
- **Production-ready remediation snippet**:
```python
# backend/smart_agri/finance/models.py (FinancialLedger.Meta.constraints)
models.CheckConstraint(
    name="financialledger_exactly_one_side_positive",
    check=(
        (models.Q(debit__gt=0) & models.Q(credit=0)) |
        (models.Q(credit__gt=0) & models.Q(debit=0))
    ),
)
```

### 2) [HIGH] Double-entry breach in cost allocation posting
- **Target file**: `backend/smart_agri/core/services/cost_allocation.py`
- **Violation**: Allocation writes only debit entries per crop plan; no paired credit entry is posted in the same transaction source.
- **Why this matters (Yemen context)**:
  - Daily manual operations and unstable connectivity require deterministic paired postings to avoid orphan debits and suspense growth.
- **Production-ready remediation snippet**:
```python
with transaction.atomic():
    # existing debit entry ...
    FinancialLedger.objects.create(
        crop_plan=plan,
        account_code=expense.account_code,
        debit=share,
        credit=Decimal("0.0000"),
        description=f"Actual Allocation: {expense.description}",
        created_by=actor,
        farm=farm,
    )
    # offset credit to payable/clearing (configurable)
    FinancialLedger.objects.create(
        crop_plan=plan,
        account_code=FinancialLedger.ACCOUNT_SECTOR_PAYABLE,
        debit=Decimal("0.0000"),
        credit=share,
        description=f"Allocation Offset: {expense.description}",
        created_by=actor,
        farm=farm,
    )
```

### 3) [HIGH] Fiscal locking gap for farm-only ledger writes
- **Target file**: `backend/smart_agri/finance/models.py`
- **Violation**: Fiscal period check in `FinancialLedger.clean()` runs only when `self.activity and self.activity.crop_plan`; farm-only/manual ledger entries can bypass period lock.
- **Why this matters (Yemen context)**:
  - Period lock integrity is critical for monthly handover (`soft-close`/`hard-close`) where post-close edits must be reversal-only.
- **Production-ready remediation snippet**:
```python
def clean(self):
    super().clean()
    from smart_agri.finance.services.core_finance import FinanceService

    if not self._state.adding:
        raise ValidationError("Immutable ledger row: updates are forbidden.")

    farm = self.farm
    if not farm and self.activity and self.activity.crop_plan:
        farm = self.activity.crop_plan.farm
    if farm:
        FinanceService.check_fiscal_period(timezone.now().date(), farm, strict=True)
```

### 4) [MEDIUM] Audit actor can be null in sensitive postings
- **Target files**:
  - `backend/smart_agri/finance/models.py`
  - `backend/smart_agri/core/services/sensitive_audit.py`
- **Violation**:
  - `FinancialLedger.created_by` is nullable.
  - `log_sensitive_mutation()` writes `user=None` if actor is missing/non-authenticated.
  - This creates forensic blind spots against requirement “user_id for EVERY change”.
- **Why this matters (Yemen context)**:
  - Manual entry chains require non-repudiation: who posted what and when, especially with offline retries.
- **Production-ready remediation snippet**:
```python
# enforce actor upstream for financial mutations
if not getattr(user, "is_authenticated", False):
    raise ValidationError("Authenticated actor is required for financial mutation.")

# optionally strengthen model
created_by = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.PROTECT,
    related_name='ledger_created_new',
    editable=False,
    null=False,
)
```

### 5) [MEDIUM] Rounding/exception handling allows silent value collapse to zero
- **Target file**: `backend/smart_agri/core/services/payroll_service.py`
- **Violation**: `_normalize_to_quarter()` catches all exceptions and returns `0.00` silently, enabling underpayment masking and “salami-slicing by bad input”.
- **Why this matters (Yemen context)**:
  - `Surra` day-rate payroll is a primary cash path; silent fallback can hide systematic skimming.
- **Production-ready remediation snippet**:
```python
from decimal import InvalidOperation

try:
    val_dec = Decimal(str(value))
except (InvalidOperation, TypeError, ValueError) as exc:
    raise ValidationError("Invalid surra value; explicit correction required.") from exc

return (val_dec * 4).quantize(Decimal("1"), rounding=ROUND_HALF_UP) / Decimal("4")
```

## Control-by-Control Verdict

### 1) Double-Entry Violations
- **Verdict**: **Partially compliant / risky**.
- Some services post paired entries (`sales_service`, `asset_service`, `core_finance.sync_activity_ledger`), but `cost_allocation` posts only one side.

### 2) Rounding Fraud (Salami Slicing)
- **Verdict**: **Partially compliant / risky**.
- Most finance paths use `Decimal` and quantize; however, silent exception fallback to zero in payroll normalization is exploitable.

### 3) Audit Trail Gaps (user_id + timestamp for EVERY change)
- **Verdict**: **Partially compliant / risky**.
- `AuditLog.timestamp` exists and append-only policy is present, but actor can be null in sensitive mutations and some state changes are not explicitly audited.

### 4) Fiscal Locking (closed periods respected)
- **Verdict**: **Partially compliant / risky**.
- Period model and status checks are strong, but farm-only `FinancialLedger` creations can bypass lock validation.

## Prioritized Repair Plan

### Phase A (Immediate - Blocker)
1. Add DB XOR check constraint for debit/credit semantics.
2. Patch `cost_allocation` to always post balanced double-entry lines inside one `transaction.atomic()` block.
3. Enforce non-null actor for all financial mutations and audit records.

### Phase B (Short-term)
4. Extend fiscal lock check to all ledger creates using resolved `farm` (even without activity linkage).
5. Replace silent payroll exception fallback with explicit validation failures and incident logging.

### Phase C (Hardening)
6. Add regression tests:
   - invalid debit/credit combinations rejected at DB level.
   - every financial posting emits audit with `user_id` and timestamp.
   - hard-closed period blocks farm-only manual postings.
   - payroll invalid surra input raises validation and does not default to zero.

## Compliance Conclusion
- **Release posture for this module: NOT 100% compliant**.
- **Required action**: implement Phase A before production promotion.
