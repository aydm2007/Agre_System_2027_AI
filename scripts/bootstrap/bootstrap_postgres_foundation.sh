#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

: "${DB_ENGINE:=django.db.backends.postgresql}"
: "${DB_HOST:=localhost}"
: "${DB_PORT:=5432}"
: "${DB_NAME:=agriasset}"
: "${DB_USER:=agriasset}"
: "${DB_PASSWORD:?DB_PASSWORD is required}"
if [ -z "${AGRIASSET_SEED_DEFAULT_PASSWORD:-}" ]; then
  AGRIASSET_SEED_DEFAULT_PASSWORD="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(12))
PY
)"
fi

export DB_ENGINE DB_HOST DB_PORT DB_NAME DB_USER DB_PASSWORD AGRIASSET_SEED_DEFAULT_PASSWORD

echo "[bootstrap] django check"
python backend/manage.py check

echo "[bootstrap] postgres foundation"
python backend/manage.py bootstrap_postgres_foundation --default-password "$AGRIASSET_SEED_DEFAULT_PASSWORD"

echo "[bootstrap] runtime probe"
python backend/manage.py runtime_probe_v21

echo "[bootstrap] attachment review snapshot"
python backend/manage.py scan_pending_attachments || true
python backend/manage.py report_due_remote_reviews || true
