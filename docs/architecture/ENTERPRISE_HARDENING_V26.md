# Enterprise Hardening v26

## What changed
- Added canonical shared GitHub Actions workflow at `.github/workflows/_shared-enterprise-ci.yml`.
- Converted overlapping CI entrypoints (`ci.yml`, `ci-cd.yml`, `backend-postgres-tests.yml`) into wrappers that call one canonical pipeline.
- Moved legacy/versioned workflows to manual-only mode to reduce CI drift.
- Added observability endpoints:
  - `/api/health/live/`
  - `/api/health/ready/`
  - `/api/health/metrics-summary/`
- Extracted frontend API helper logic from `frontend/src/api/client.js` into dedicated modules to start modular decomposition.
- Removed additional stale settings references from docs and utility scripts.

## Why this matters
These changes reduce operational drift, improve deployment confidence, and begin the controlled breakup of oversized integration files without changing business behavior.

## Remaining work
- Break down `frontend/src/api/client.js` further by domain modules.
- Split `core` bounded context into narrower packages.
- Add OpenTelemetry/Prometheus exporters.
- Replace broad exception handlers with typed domain failures.
- Introduce contract tests for integrations and offline replay.
