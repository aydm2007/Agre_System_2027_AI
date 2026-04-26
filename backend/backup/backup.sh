#!/usr/bin/env bash
set -euo pipefail

# Required env (from docker-compose.prod.yml)
: "${POSTGRES_HOST:?POSTGRES_HOST is required}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"

BACKUP_DIR="${BACKUP_DIR:-/backups}"
INTERVAL_MINUTES="${BACKUP_INTERVAL_MINUTES:-360}"   # 6 hours default
RETENTION_COUNT="${BACKUP_RETENTION_COUNT:-30}"      # keep last 30 backups

mkdir -p "$BACKUP_DIR"

export PGPASSWORD="$POSTGRES_PASSWORD"

log() { echo "[backup] $(date -Iseconds) $*"; }

run_backup() {
  local ts
  ts="$(date +%Y%m%d_%H%M%S)"
  local out="$BACKUP_DIR/${POSTGRES_DB}_${ts}.sql.gz"

  log "Starting pg_dump -> $out"
  # --no-owner and --no-privileges keep dumps portable across environments
  pg_dump -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-privileges | gzip -9 > "$out"
  log "Backup completed"

  # Retention (keep most recent N)
  local count
  count=$(ls -1 "$BACKUP_DIR"/*.sql.gz 2>/dev/null | wc -l | tr -d ' ')
  if [[ "$count" -gt "$RETENTION_COUNT" ]]; then
    local remove
    remove=$((count - RETENTION_COUNT))
    log "Applying retention: removing $remove old backups (keep $RETENTION_COUNT)"
    ls -1t "$BACKUP_DIR"/*.sql.gz | tail -n "$remove" | xargs -r rm -f
  fi
}

log "Backup loop started. interval=${INTERVAL_MINUTES}m retention=${RETENTION_COUNT}"

while true; do
  run_backup || log "ERROR: backup failed (will retry next interval)"
  sleep "$((INTERVAL_MINUTES*60))"
done
