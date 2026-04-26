# Enterprise Hardening V28

## What changed
- Extracted labor synchronization and identityless costing logic out of `activity_service.py` into focused support modules.
- Added `RequestObservabilityMiddleware` to stamp every response with request id and response time.
- Expanded `metrics-summary` endpoint with request id, timestamp, and domain counts.
- Added regression tests for request observability and labor normalization helpers.

## Why it matters
These changes reduce service-file bloat, improve transaction-path readability, and make production tracing materially easier during incidents.
