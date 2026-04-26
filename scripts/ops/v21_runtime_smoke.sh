#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

export DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-smart_agri.settings}

python backend/manage.py check
python backend/manage.py showmigrations --plan
python backend/manage.py runtime_probe_v21
python backend/manage.py scan_pending_attachments
python backend/manage.py report_due_remote_reviews
