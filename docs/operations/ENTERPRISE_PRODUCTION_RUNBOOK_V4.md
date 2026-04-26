# Enterprise Production Runbook (V4 Candidate)

## Scope
This runbook defines the minimum production contract for AgriAsset V4 as an enterprise candidate.

## Pre-go-live checklist
1. Provision PostgreSQL, Redis, web, nginx, and backup worker.
2. Load secrets from environment or a centralized secrets manager.
3. Run `python manage.py check --deploy` using production settings.
4. Run migrations and confirm `showmigrations` is clean.
5. Run static asset collection.
6. Validate login, Daily Log, Petty Cash, Supplier Settlement, Fixed Assets, and Fuel dashboards.
7. Capture release evidence in the readiness report.

## Minimum runtime controls
- HTTPS only.
- `DEBUG=False`.
- explicit `ALLOWED_HOSTS`.
- secure cookies enabled.
- audit retention enabled.
- centralized logs and alerting enabled.
- backup and restore drill recorded.

## Go-live command path
```bash
cp .env.enterprise.example .env.prod
# replace placeholders before use

docker compose -f docker-compose.prod.yml -f docker-compose.enterprise.yml up -d --build
```

## Rollback posture
- Keep the previous application image and the previous database backup.
- If the release fails: stop app traffic, restore previous image, restore database only if forward-only rollback is impossible.
- Record incident and release deviation in the audit/change log.
