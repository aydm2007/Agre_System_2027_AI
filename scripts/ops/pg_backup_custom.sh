#!/usr/bin/env bash
set -euo pipefail

: "${POSTGRES_HOST:=db}"
: "${POSTGRES_PORT:=5432}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
: "${BACKUP_DIRECTORY:=./backups}"

mkdir -p "$BACKUP_DIRECTORY"
STAMP="$(date +%Y%m%d_%H%M%S)"
ARCHIVE="$BACKUP_DIRECTORY/${POSTGRES_DB}_${STAMP}.dump"
export PGPASSWORD="$POSTGRES_PASSWORD"

pg_dump \
  --host "$POSTGRES_HOST" \
  --port "$POSTGRES_PORT" \
  --username "$POSTGRES_USER" \
  --format=custom \
  --file "$ARCHIVE" \
  "$POSTGRES_DB"

echo "Backup created: $ARCHIVE"
