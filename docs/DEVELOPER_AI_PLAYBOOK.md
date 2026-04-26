# Developer & AI Assistant Playbook (YECO Edition)

> Reference class: public developer/agent playbook.
> This document is guidance for contributors and AI assistants. It does not outrank `AGENTS.md`, `PRD V21`, doctrine, or latest canonical evidence.
> Canonical public docs format remains `HTML/MkDocs`; any Word delivery copy is derived only.

This playbook helps human contributors and AI coding agents collaborate safely in AgriAsset.

## 1) Work intake protocol

- Confirm task scope and target module (`core`, `finance`, `sales`, etc.).
- For finance/treasury work, assume **forensic criticality**.
- Read in order:
  1. `AGENTS.md`
  2. `.agent/skills/agri_guardian/SKILL.md`
  3. `docs/PRODUCTION_RELEASE_GATE.md`

## 2) Non-negotiable invariants

- No floats in financial mutations.
- No mutable ledger edits (`UPDATE`/`DELETE` forbidden for immutable rows).
- Farm isolation is mandatory in API, service, and persistence behavior.
- All financial mutation endpoints require idempotency behavior.

## 3) Treasury module conventions

- `CashBox` is operationally read-only through API; balances change via posted transactions only.
- `TreasuryTransaction` is append-only.
- Posting must be double-entry balanced and traceable.
- `party_*` (treasury) and `entity_*` (ledger) dimensions should be passed whenever available.

## 4) Minimal pre-PR evidence

Run and report:

```bash
python manage.py check
python scripts/check_no_float_mutations.py
python scripts/check_idempotency_actions.py
python scripts/check_farm_scope_guards.py
python scripts/verification/detect_zombies.py
```

If a command is blocked by environment (e.g., DB unavailable), report the exact command and reason.

## 5) PR quality bar

Every PR should include:

- concise summary of changed behavior
- compliance command outcomes
- before/after impact on:
  - idempotency
  - fiscal close behavior
  - tenant isolation
  - audit trail completeness
