# Phase 6 — Schema Hygiene & Forensic Verification

**Scope:** Verify zombie tables, ghost triggers, and RLS coverage against the authoritative schema.

## Required Checks
- **Zombie tables:** Run the detector and review any orphaned tables.
- **Ghost triggers:** Confirm triggers do not duplicate Python-side business logic.
- **RLS coverage:** Validate RLS policies exist on tenant-sensitive tables.

## Commands (Run in the production-like DB environment)
- `python scripts/verification/detect_zombies.py`
- `python manage.py nightly_integrity_check`
- `python manage.py diagnostic_system`

## Status
- **Pending execution** in this environment (requires database access).

## Follow-ups
- Record the outputs and attach them to this report before release.
- If zombies/ghosts are detected, resolve via migrations or explicit cleanup commands.
