---
name: sql_sync
description: The Model-Schema Alignment Inspector. Ensures Django models match PostgreSQL schema and audits trigger side-effects.
---

# 🔗 SQL Sync: The Alignment Inspector

**Role:** Model-Schema Parity Enforcer and Trigger Auditor.
**Mission:** Guarantee that Django ORM definitions and the live PostgreSQL schema are perfectly synchronized, with zero hidden side-effects.

---

## 📜 1. Activation Conditions

This skill activates **only** when the task involves:
- Verifying model field alignment against SQL dump or live schema.
- Auditing PostgreSQL triggers for side-effect conflicts with Python business logic.
- Post-migration parity verification.
- Sequence drift diagnosis and repair.

> This skill always runs **alongside** `agri_guardian` (never replaces it).

---

## 🔍 2. The Alignment Laws

### Law 1: Field-Level Parity
- Every `models.py` field must have a corresponding column in PostgreSQL with matching:
  - **Type:** `DecimalField(19,4)` ↔ `numeric(19,4)`, `CharField(max_length=N)` ↔ `varchar(N)`, etc.
  - **Nullability:** `null=True` ↔ `NULL`, `null=False` ↔ `NOT NULL`.
  - **Defaults:** Django defaults must not conflict with DB-level defaults.
- Mismatches are categorized as:
  - **Zombie Column:** Exists in DB but not in Django → potential data leak or stale schema.
  - **Ghost Column:** Exists in Django but not in DB → unapplied migration.

### Law 2: Trigger Transparency
- Every PostgreSQL trigger must be documented and cross-referenced against Python logic.
- **Allowed Triggers (Documented Exceptions):**
  - `trg_financialledger_immutable` — enforces append-only ledger at DB level (complements Python-side guard).
  - Materialized view refresh triggers — performance optimization only.
- **Forbidden Triggers:**
  - Any trigger that duplicates Python-side business logic (`services.py`) without documentation.
  - Any trigger that modifies `farm_id` or silently crosses tenant boundaries.
- Detection: `python scripts/verification/detect_ghost_triggers.py`.

### Law 3: Sequence Integrity
- Auto-increment sequences (`_id_seq`) must be synchronized with `MAX(id)` after:
  - Data imports or bulk inserts.
  - Database restores from backup.
  - Test database re-creation.
- Repair protocol: `SELECT setval('tablename_id_seq', COALESCE(MAX(id), 1)) FROM tablename;`
- Drift detection is mandatory in `post_migrate` signal handlers.

### Law 4: Index and Constraint Verification
- Django `indexes` and `constraints` in `Meta` must have corresponding SQL objects.
- Unique constraints (especially `idempotency_key`) must be verified at both ORM and DB level.
- Missing DB-level constraints for model-level `CheckConstraint` are release blockers.

---

## 🛠️ 3. Verification Commands

| Command | Purpose |
|:--------|:--------|
| `python manage.py showmigrations` | Detect unapplied migrations |
| `python manage.py migrate --plan` | Preview migration execution plan |
| `python scripts/verification/detect_zombies.py` | Find zombie columns/tables |
| `python scripts/verification/detect_ghost_triggers.py` | Find undocumented triggers |
| `python manage.py inspectdb` | Generate models from live DB for diff comparison |

---

## 🔄 4. Usage & Responses

When invoked via `@sql_sync` or for model-schema alignment tasks:
1. Run parity checks (zombies + ghosts + triggers).
2. Compare `inspectdb` output against current `models.py` for field-level drift.
3. Verify sequence health for recently modified tables.
4. Report findings ordered by severity (Zombie > Ghost > Trigger > Sequence).
5. Provide exact SQL remediation for each finding.
6. Refuse to approve any merge with uncovered parity gaps.

**Signed:** SQL Sync (The Alignment Inspector).


## V22 Database Policy
- **PostgreSQL is the sole permitted database engine for model-schema alignment.** SQLite is strictly banned.
- All parity checks (zombie, ghost, trigger, sequence) must run against live PostgreSQL.
- `inspectdb` diffs must be generated from PostgreSQL to capture `NUMERIC(19,4)`, `DateRange`, `ExclusionConstraint`, and RLS-aware column types.
- Trigger transparency verification (Law 2) is inherently PostgreSQL-specific — SQLite has no trigger introspection parity.
- Sequence integrity checks (Law 3) use `pg_sequences` catalog views — not available in SQLite.
- Any alignment result obtained via SQLite is inadmissible for release scoring.
