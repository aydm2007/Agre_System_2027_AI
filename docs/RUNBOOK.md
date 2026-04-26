# AgriAsset V21 Operational Runbook

> Reference class: public operational guide.
> This file is not a higher-order canonical source than `PRD V21`, `AGENTS.md`, doctrine, or the
> latest canonical evidence. For release authority, always defer to `docs/evidence/closure/latest/`.

## 1. Startup

### Backend
```bash
cd backend
python manage.py check --deploy
python manage.py migrate --noinput
python manage.py collectstatic --noinput
gunicorn smart_agri.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120
```

### Frontend
```bash
cd frontend
npm run build
```

### Windows canonical verification bootstrap
```powershell
& .\scripts\windows\Resolve-BackendDbEnv.ps1
python backend/manage.py migrate --noinput
python backend/manage.py runserver
```

## 2. Health and smoke endpoints
- `/api/health/`
- `/api/health/live/`
- `/api/health/ready/`
- `/api/schema/`
- `/api/docs/`

Path policy:
- auth and health live under `/api/`
- business routers live under `/api/v1/`

## 3. Canonical verification commands
```bash
python scripts/verification/check_compliance_docs.py
python backend/manage.py verify_static_v21
python backend/manage.py verify_release_gate_v21
python backend/manage.py verify_axis_complete_v21
```

## 4. Backups and restore
```bash
./scripts/backup_db.sh
./scripts/restore_db.sh backups/agriasset_YYYYMMDD_HHMMSS.sql.gz
```

## 5. Common checks
```bash
curl http://localhost:8000/api/health/
python backend/manage.py showmigrations --plan
python backend/manage.py runtime_probe_v21
python backend/manage.py release_readiness_snapshot
python backend/manage.py scan_pending_attachments
```

## 6. Common incidents

### Migrations out of sync
```bash
python backend/manage.py showmigrations --plan
python backend/manage.py migrate --noinput
```

### Attachment backlog or quarantine growth
```bash
python backend/manage.py scan_pending_attachments
python backend/manage.py release_readiness_snapshot
```

### Governance maintenance backlog
```bash
python backend/manage.py run_governance_maintenance_cycle --dry-run
```

### Browser proof drift
- On Windows, always preload DB env with `Resolve-BackendDbEnv.ps1`.
- Do not assume a developer-local migrated database state.
- Re-run canonical gates before treating browser fixes as closure.

## 7. Operational contacts
| Role | Responsibility |
|------|----------------|
| System administrator | restart, migrations, backups, runtime verification |
| Farm/sector finance leadership | governed financial close and release review |
| Engineering team | code fixes, regressions, and evidence restoration |
