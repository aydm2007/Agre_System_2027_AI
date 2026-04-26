# Roadmap to 100/100

## Implemented in this upgrade
- Unified host env parsing across base and production settings.
- Fixed CI deploy-check settings path and removed silent success pattern.
- Added log directory bootstrap for production logging.
- Hardened event publishing to run after transaction commit by default.
- Removed selected legacy DJANGO_SETTINGS_MODULE references.

## Remaining high-priority phases
1. Split oversized frontend API client into domain adapters.
2. Consolidate CI/CD workflows into one canonical pipeline.
3. Break down oversized backend services and reporting endpoints.
4. Add observability stack: OpenTelemetry, Prometheus, Grafana, Sentry.
5. Formalize integration contracts, outbox pattern, and IoT/weather/GIS connectors.
6. Add disaster-recovery drills and upgrade/rollback playbooks with evidence.
