# Final World-Class Release Playbook

## 1) Platform services
- Run database, redis, backend, celery worker, and celery beat.
- Enable `STRICT_FARM_SCOPE_HEADERS=true` in production.
- Set `INTEGRATION_HUB_PUBLISHER=webhook` only after validating downstream receivers.

## 2) Release evidence
- `python manage.py release_readiness_snapshot`
- `python manage.py dispatch_outbox --batch-size 200`
- `python manage.py retry_dead_letters --limit 50` only when recovery is required
- `python manage.py purge_dispatched_outbox --older-than-hours 168 --dry-run` before scheduled cleanup

## 3) Monitoring
- Scrape `/api/health/prometheus/` with Prometheus
- Import `ops/grafana/agriasset-platform-dashboard.json` into Grafana
- Monitor dead letters, retry-ready outbox events, and strict farm-scope mode

## 4) Production acceptance gate
- `readyz` returns ok
- outbox dead letters = 0 or explicitly triaged
- release snapshot generated successfully
- background worker and beat are both healthy
