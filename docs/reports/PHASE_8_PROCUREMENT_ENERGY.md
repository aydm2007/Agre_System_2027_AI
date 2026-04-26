# Phase 8 — Procurement & Energy Controls

**Scope:** Enforce approval controls for procurement-related spends and energy assets, with audit visibility.

## Requirements
- Multi-approval for purchases above farm thresholds.
- Technical approval for regulated inputs (pesticides, diesel).
- Depreciation of energy assets (solar) tracked via monthly runs.

## Current Coverage
- Asset depreciation is supported via `AssetService.run_monthly_depreciation`.
- Approval workflows for procurement/energy require explicit configuration and UI wiring.

## Follow-ups
- Add procurement approval workflow (warning/critical thresholds) and tie to budget codes.
- Implement technical approval fields for regulated inputs with audit logs.
- Surface energy asset depreciation status per farm dashboard.
