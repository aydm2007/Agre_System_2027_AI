# Backup and Restore Runbook (V4 Candidate)

## Backup standard
Use PostgreSQL custom format backups (`pg_dump -Fc`) for production archival flexibility and selective restore.

## Backup command
```bash
POSTGRES_HOST=db POSTGRES_PORT=5432 POSTGRES_DB=smart_agri_db POSTGRES_USER=postgres POSTGRES_PASSWORD=*** \
  bash scripts/ops/pg_backup_custom.sh
```

## Restore command
```bash
POSTGRES_HOST=db POSTGRES_PORT=5432 POSTGRES_DB=smart_agri_restore_verify POSTGRES_USER=postgres POSTGRES_PASSWORD=*** \
  bash scripts/ops/pg_restore_custom.sh ./backups/example.dump
```

## Drill expectations
- backup file exists and is non-zero size
- restore completes without fatal errors
- target DB boots under Django migrations inspection
- drill evidence is attached to the release package

## Retention
- daily backups retained for 14 days minimum
- one weekly retained for 8 weeks minimum
- one monthly retained for 12 months minimum
