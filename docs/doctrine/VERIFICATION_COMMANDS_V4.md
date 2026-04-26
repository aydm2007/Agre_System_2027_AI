# Verification Commands V4

## Static gate
```bash
make verify-enterprise-static
```

## Full gate in provisioned environment
```bash
make verify-release-gate
```

## Enterprise compose startup
```bash
docker compose -f docker-compose.prod.yml -f docker-compose.enterprise.yml up -d --build
```

## Required runtime proofs for 100/100
```bash
docker compose -f docker-compose.prod.yml -f docker-compose.enterprise.yml exec web python manage.py showmigrations
docker compose -f docker-compose.prod.yml -f docker-compose.enterprise.yml exec web python manage.py migrate --plan
docker compose -f docker-compose.prod.yml -f docker-compose.enterprise.yml exec web python manage.py check --deploy
```

## Backup / restore drill
```bash
bash scripts/ops/pg_backup_custom.sh
bash scripts/ops/pg_restore_custom.sh ./backups/example.dump
```
