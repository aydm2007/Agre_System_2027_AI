#!/usr/bin/env bash
# ============================================================================
# AgriAsset ERP — Database Backup Script
# ============================================================================
# Usage:
#   ./scripts/backup_db.sh                     # Default backup to ./backups/
#   ./scripts/backup_db.sh /path/to/dir        # Custom backup directory
#   PGPASSWORD=xxx ./scripts/backup_db.sh      # Use env var for password
#
# Retention: keeps last 7 backups (configurable via BACKUP_RETAIN_COUNT)
# ============================================================================

set -euo pipefail

# ---------- Configuration ----------
DB_NAME="${DB_NAME:-agriasset}"
DB_USER="${DB_USER:-postgres}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
BACKUP_DIR="${1:-$(dirname "$0")/../backups}"
BACKUP_RETAIN_COUNT="${BACKUP_RETAIN_COUNT:-7}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.sql.gz"

# ---------- Prepare ----------
mkdir -p "$BACKUP_DIR"

echo "╔════════════════════════════════════════╗"
echo "║  AgriAsset Backup — $(date '+%Y-%m-%d %H:%M')    ║"
echo "╠════════════════════════════════════════╣"
echo "║  DB: ${DB_NAME}@${DB_HOST}:${DB_PORT}      "
echo "║  Target: ${BACKUP_FILE}                    "
echo "╚════════════════════════════════════════╝"

# ---------- Dump ----------
echo "[1/3] Creating compressed backup..."
pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --format=custom \
    --compress=9 \
    --no-owner \
    --no-privileges \
    --verbose 2>/dev/null \
    | gzip > "$BACKUP_FILE"

BACKUP_SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
echo "    ✅ Backup complete: ${BACKUP_SIZE}"

# ---------- Verify ----------
echo "[2/3] Verifying backup integrity..."
if gzip -t "$BACKUP_FILE" 2>/dev/null; then
    echo "    ✅ Backup integrity verified"
else
    echo "    ❌ BACKUP CORRUPTED — check disk space"
    exit 1
fi

# ---------- Retention ----------
echo "[3/3] Pruning old backups (keeping last ${BACKUP_RETAIN_COUNT})..."
cd "$BACKUP_DIR"
ls -1t ${DB_NAME}_*.sql.gz 2>/dev/null | tail -n +$((BACKUP_RETAIN_COUNT + 1)) | while read old_backup; do
    echo "    🗑️ Removing: $old_backup"
    rm -f "$old_backup"
done

echo ""
echo "✅ Backup complete: ${BACKUP_FILE}"
echo "   Size: ${BACKUP_SIZE}"
echo "   Backups retained: $(ls -1 ${DB_NAME}_*.sql.gz 2>/dev/null | wc -l)"
