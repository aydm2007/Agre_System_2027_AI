# Fiscal Period Operations UI

This doctrine is the operator contract for fiscal-year visibility, period close lifecycle,
and year-opening maintenance inside the AgriAsset finance surface.

## Canonical UI entry points

- `/finance/fiscal-periods`
  - Primary closure and reopen workspace.
  - Shows all periods for the selected farm and fiscal year.
  - Supports `soft-close`, `hard-close`, and governed `reopen`.

- `/finance/fiscal-years`
  - Read-side fiscal year registry for the selected farm.
  - Used to verify whether the year record exists and whether `is_closed` is set.

- `/settings?tab=fiscalPeriods`
  - Settings tab alias for finance and administrative users who already work from the settings shell.

- `/settings/fiscal-periods`
  - Direct alias to the same fiscal-period workspace for deep links and support handoff.

## Navigation visibility

- The primary navigation exposes `إغلاقات الفترات المالية` and links it to
  `/finance/fiscal-periods`.
- The settings workspace exposes a `الفترات المالية` tab that renders the same managed UI.

## Operational truth

An open fiscal year flag alone is not enough for daily execution.

Daily logs and governed financial posting require:

1. The target `FiscalYear` to exist for the farm and year.
2. The specific monthly `FiscalPeriod` for the transaction date to exist.
3. The target period status to be `open`.
4. The fiscal year itself to remain not closed.

If a farm has fiscal year `2026` marked open but only period `2026-04` exists,
then daily execution on `2026-05-01` still fails because the May period is missing.

## Canonical maintenance command

Use the governed maintenance command to backfill or reopen fiscal coverage:

```bash
python backend/manage.py ensure_fiscal_year_open --farm sardud --year 2026 --reason "Open 2026 for daily execution"
```

Reopen closed periods or a closed year only under explicit audit reason:

```bash
python backend/manage.py ensure_fiscal_year_open --farm sardud --year 2026 --reopen-closed --actor-username admin --reason "Reopen 2026 after governed review"
```

## Governance requirements

- Close lifecycle remains `open -> soft-close -> hard-close`.
- Reopen remains exceptional and must leave `AuditLog` evidence.
- The UI must not allow direct mutable editing of fiscal periods.
- Year-opening maintenance must preserve service-layer governance and append-only audit evidence.
