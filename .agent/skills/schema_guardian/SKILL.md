---
name: schema_guardian
description: The unified DBA & Schema Inspector. Enforces migration parity, RLS coverage, trigger transparency, sequence integrity, and policy metadata readiness.
---

# Schema Guardian

Role: Database Guardian, Schema Enforcer, and Trigger Auditor.
Mission: Guarantee zero drift between Django ORM definitions and PostgreSQL schema, with zero hidden side-effects.

## 1. Activation Conditions
This skill activates when the task involves:
- post-migration schema hygiene verification
- zombie table/ghost column detection
- RLS policy coverage verification or extension
- PostgreSQL trigger auditing
- sequence drift diagnosis and repair
- model-vs-schema alignment verification
- new policy metadata for governance, attachment lifecycle, archive state, or thresholds

This skill always runs alongside `agri_guardian`.

## 2. The Schema Laws
### Law 1: Absolute Parity
- Zombie columns/tables and ghost columns remain blockers.
- Materialized views are excluded from zombie checks but validated to exist.

### Law 2: Field-Level Parity
- Django field type, nullability, and defaults must align with PostgreSQL.
- If V15 introduces role, threshold, attachment class, retention class, archive state, or governance-policy fields, they must ship with schema parity and backward-safe migrations.

### Law 3: Trigger Transparency
- Business logic MUST live in Python — not hidden PostgreSQL triggers.
- Allowed triggers remain documented exceptions only.

### Law 4: Tenant Fences
- Every tenant-sensitive table requires `farm_id` or an equivalent documented scoping strategy.
- New tenant-sensitive tables must ship with Python farm-scope guards and DB-level RLS in the same change set.

### Law 5: Sequence Integrity
- Sequences must stay aligned after imports, restores, and data repair.

### Law 6: Index and Constraint Verification
- Django indexes and constraints must have corresponding SQL objects.
- Missing DB-level constraints for declared business checks are release blockers.

### Law 7: Policy Metadata Readiness
When V15 governance introduces metadata such as:
- attachment evidence class
- retention class
- legal hold state
- archive tier/state
- farm thresholds
- role-delegation or acting-finance flags

then schema review must confirm:
- fields exist where promised
- defaults are safe
- migration rollout is backward compatible
- reporting and filters can read them without hidden schema debt

## 3. Verification Commands
| Command | Purpose |
|:--------|:--------|
| `python manage.py showmigrations` | Detect unapplied migrations |
| `python manage.py migrate --plan` | Preview migration execution plan |
| `python manage.py check` | Django system checks |
| `python manage.py inspectdb` | Generate models from live DB for alignment diff |
| `python scripts/verification/detect_zombies.py` | Find zombie columns/tables |
| `python scripts/verification/detect_ghost_triggers.py` | Find undocumented triggers |

## 4. Usage & Responses
When invoked:
1. run parity checks (zombies + ghosts + triggers + sequences)
2. compare `inspectdb` output against current `models.py`
3. verify RLS coverage for affected tables
4. verify policy metadata fields promised by doctrine and PRD
5. report findings ordered by severity
6. provide exact SQL or migration remediation
7. refuse approval when schema debt would make doctrine claims false


## V15 Phase-2 Focus
- archive/quarantine/restoration metadata must ship with safe migrations and backward compatibility


## V15 delta
- V15 governed schema state.
- SIMPLE must not auto-register full finance routes.
- STRICT final posting actions honor `approval_profile` and may require sector-final authority.


## V16 Addendum
- Respect profile-aware approval chains and avoid collapsing `basic`, `tiered`, and `strict_finance` farms into one synthetic ladder.
- Treat `run_governance_maintenance` as the canonical operational entrypoint for overdue approvals, remote-review drift, and attachment lifecycle queues.


## V22 Database Policy
- **PostgreSQL is the sole permitted database engine for all schema verification.** SQLite is strictly banned.
- All verification commands in §3 must be executed against a live PostgreSQL connection — never SQLite.
- Zombie/ghost detection, trigger auditing, and RLS policy verification inherently depend on PostgreSQL-specific features (`btree_gist`, `ExclusionConstraint`, `SET app.current_farm_id`, etc.) that SQLite cannot replicate.
- `inspectdb` alignment diffs must be generated from PostgreSQL to capture `NUMERIC` precision, `DateRange`, and custom constraint types.
- Migration health checks (`migrate --plan`, `makemigrations --check --dry-run`) must target PostgreSQL to ensure trigger and constraint SQL is validated.
- Any schema review that was performed under SQLite must be repeated against PostgreSQL before scoring as `PASS`.
