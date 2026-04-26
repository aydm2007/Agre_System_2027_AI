# AgriAsset – Install & Run (V4 enterprise candidate)

This guide is the current bootstrap contract for the repository. It is intentionally evidence-oriented:
follow these steps, then run the static and runtime verification gates.

## Prerequisites

- Python 3.11
- PostgreSQL 16+
- Node 18+
- Docker Desktop / Docker Engine + Compose

## Option A — Docker development

```bash
cp .env.docker.example .env.docker
docker compose build
docker compose up -d
python backend/manage.py verify_static_v21
```

## Option B — Enterprise candidate stack

```bash
cp .env.enterprise.example .env.prod
# replace all placeholders before use

docker compose -f docker-compose.prod.yml -f docker-compose.enterprise.yml up -d --build
```

Then, in the provisioned environment, run:

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.enterprise.yml exec web python manage.py showmigrations
docker compose -f docker-compose.prod.yml -f docker-compose.enterprise.yml exec web python manage.py migrate --plan
docker compose -f docker-compose.prod.yml -f docker-compose.enterprise.yml exec web python manage.py check --deploy
```

## Local development

### Backend
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Verification

Static:
```bash
python backend/manage.py verify_static_v21
```

Runtime in provisioned environment:
```bash
python backend/manage.py verify_release_gate_v21
```

Windows PowerShell fallback:
```powershell
& .\scripts\windows\Resolve-BackendDbEnv.ps1
python backend/manage.py verify_static_v21
python backend/manage.py verify_release_gate_v21
```

## Backup / Restore

Use PostgreSQL custom-format dumps for production drills:
```bash
bash scripts/ops/pg_backup_custom.sh
bash scripts/ops/pg_restore_custom.sh ./backups/example.dump
```

## Notes

- `100/100` remains evidence-gated and requires runtime proof, not only structural updates.
- Documentary-cycle mapping remains tracked in `docs/doctrine/DOCX_CODE_TRACEABILITY_MATRIX_V5.md`.
- The latest readiness summary is `docs/doctrine/V4_COMPLETION_READINESS.md`.


## Arabic enterprise shell

This repository now carries an explicit Arabic-first contract:
- backend locale: `ar`
- frontend shell: `lang=ar`, `dir=rtl`
- enterprise defaults: `DEFAULT_LOCALE=ar_YE`, `DEFAULT_DIRECTION=rtl`, `DEFAULT_TIMEZONE=Asia/Aden`
- quick Arabic guide: `README_AR.md`

For the strongest static contract run:
```bash
python backend/manage.py verify_static_v21
```
