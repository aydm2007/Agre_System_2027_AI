#!/usr/bin/env bash
# ============================================================================
# AgriAsset ERP — Database Restore Script
# ============================================================================
# Usage:
#   ./scripts/restore_db.sh backups/agriasset_20260304_120000.sql.gz
#
# ⚠️  WARNING: This will DROP and recreate the target database!
# ============================================================================

set -euo pipefail

if [ -z "${1:-}" ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    echo "Available backups:"
    ls -lth backups/*.sql.gz 2>/dev/null || echo "  (none found in ./backups/)"
    exit 1
fi

BACKUP_FILE="$1"
DB_NAME="${DB_NAME:-agriasset}"
DB_USER="${DB_USER:-postgres}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ File not found: $BACKUP_FILE"
    exit 1
fi

echo "╔════════════════════════════════════════╗"
echo "║  ⚠️  AgriAsset RESTORE                ║"
echo "╠════════════════════════════════════════╣"
echo "║  From: ${BACKUP_FILE}                  "
echo "║  To:   ${DB_NAME}@${DB_HOST}:${DB_PORT}"
echo "╚════════════════════════════════════════╝"
echo ""
echo "⚠️  This will DROP database '${DB_NAME}' and restore from backup."
read -p "Type 'YES' to confirm: " confirmation

if [ "$confirmation" != "YES" ]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "[1/3] Dropping existing database..."
dropdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" --if-exists "$DB_NAME"

echo "[2/3] Creating fresh database..."
createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME"

echo "[3/3] Restoring from backup..."
gunzip -c "$BACKUP_FILE" | pg_restore \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --no-owner \
    --no-privileges \
    --verbose 2>/dev/null

echo ""
echo "✅ Restore complete!"
echo "   Next steps:"
echo "   1. python manage.py migrate  (apply any pending migrations)"
echo "   2. python manage.py check    (verify system integrity)"
