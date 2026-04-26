# DR / BCP Runbook

## Objective
Ensure service continuity for AgriAsset with measured recovery objectives.

## Targets
| service | RTO_target_minutes | RPO_target_minutes |
|---|---:|---:|
| PostgreSQL database | 120 | 30 |
| Backend API | 90 | 30 |
| Frontend app | 60 | 60 |

## Failure Scenarios
1. DB corruption or accidental destructive operation.
2. Backend host/app outage.
3. Environment-wide outage requiring full stack restore.

## Backup Procedure
1. Verify DB connectivity and disk free space.
2. Execute backup command (environment-specific):
   - `pg_dump` with timestamped filename.
3. Store backup in protected storage path.
4. Record checksum and backup completion time.

## Restore Procedure
1. Provision clean target database.
2. Restore from latest valid backup (`psql`/`pg_restore`).
3. Run migrations parity check:
   - `python backend/manage.py showmigrations`
   - `python backend/manage.py migrate --plan`
4. Run integrity checks:
   - `python backend/manage.py check`
   - `python scripts/verification/detect_zombies.py`

## Monthly Drill Requirements
- Frequency: monthly.
- Required evidence file: `docs/reports/DR_DRILL_<YYYY-MM-DD>.md`
- Mandatory fields in drill evidence:
  - `DRILL_DATE`
  - `SCENARIO`
  - `RTO_TARGET_MINUTES`
  - `RTO_ACTUAL_MINUTES`
  - `RPO_TARGET_MINUTES`
  - `RPO_ACTUAL_MINUTES`
  - `RESULT`
  - `EVIDENCE_COMMANDS`

## Escalation
- If `RTO_ACTUAL_MINUTES > RTO_TARGET_MINUTES` or `RPO_ACTUAL_MINUTES > RPO_TARGET_MINUTES`, result is FAIL and requires corrective action within 7 days.
