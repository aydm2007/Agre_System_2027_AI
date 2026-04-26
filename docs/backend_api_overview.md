# Backend API Structure (Updated 2025-11-12)

## Why this change?

Historically the repository carried multiple experimental copies of the Django REST API (`api_new.py`, `api_final.py`, `api_fixed.py`, `api_quality.py`, `api_simple.py`, `api_simple_fixed.py`). The files drifted away from one another and created confusion during reviews and deployments.

As of **2025‑11‑12** the redundant modules have been removed. The project now exposes a **single authoritative entry-point**:

- `backend/smart_agri/core/api.py`

All viewsets, routers, and schema registrations must live in this module (or be imported by it from subpackages). This guarantees that:

- Documentation (OpenAPI/Swagger) always matches the deployed code.
- Tests exercise the exact code-paths that reach production.
- Security reviews focus on one surface area instead of half a dozen forks.

## Best practices going forward

1. **Modularise with packages, not new files**: when adding a domain (e.g. `inventory`, `trees`, `reports`), create a subpackage inside `backend/smart_agri/core/api/` and import the viewsets in `api.py`.
2. **Keep routers centralised**: register new routes in one place so middleware, throttling, and versioning remain consistent.
3. **Document public endpoints**: every viewset should include docstrings + Spectacular annotations; update `docs/system_overview.md` when you add/delete resources.
4. **Lean on tests**: extend the suites under `backend/smart_agri/core/tests/` instead of cloning files for “safe” changes.

Following the above keeps the service maintainable and supports the goal of a 95‑100 % functional coverage score referenced in stakeholder reviews.
