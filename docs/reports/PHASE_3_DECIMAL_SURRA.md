# Phase 3 — Decimal + Daily-Rate (Surra) Enforcement

**Scope:** Eliminate float usage in finance/inventory mutation paths and enforce deterministic Decimal rounding in cost calculations.

## What Changed
- **Inventory mutations:** Reject float inputs for quantity/unit-cost in adjust/transfer/receive operations and require Decimal-safe values.
- **Costing strictness:** Enforced Decimal conversion for shifts, machine hours, and planted area with `ROUND_HALF_UP` quantization for all cost components and totals.

## Yemen Context Alignment
- **Daily-rate priority:** Labor costing continues to use shifts × daily rate (Surra), with strict Decimal handling.
- **Weak network safety:** Deterministic rounding avoids inconsistent results when retries occur.

## Follow-ups
- Add tests for float rejection in inventory mutation endpoints.
- Extend strict Decimal validation to any remaining mutation endpoints that accept numeric inputs.
