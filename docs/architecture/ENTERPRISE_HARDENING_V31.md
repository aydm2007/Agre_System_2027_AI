# Enterprise Hardening V31

## What changed
- Extracted `finance/api_ledger_support.py` to reduce orchestration and domain-math pressure inside `api_ledger.py`.
- Centralized ledger queryset shaping, summary aggregation, farm-action resolution, and material variance calculations.
- Tightened observability exception handling by replacing broad runtime catches with typed cache/database failure handling.
- Added focused tests for ledger support math and summaries.

## Why it matters
This pass improves modularity in one of the most financially sensitive surfaces while also reducing broad runtime exception handling in observability endpoints.
