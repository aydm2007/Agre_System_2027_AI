# Observability and Security Baseline (V4 Candidate)

## Required controls
- application audit logging for sensitive mutations
- centralized log shipping
- alerting for authentication anomalies, fiscal close errors, backup failures, and 5xx bursts
- principle-of-least-privilege for runtime identities
- secrets are not committed to source control
- health checks on db, redis, and web
- release evidence retained with build metadata

## Minimum telemetry
- request latency
- 4xx/5xx rates
- task failures (Celery)
- database connection saturation
- backup job success/failure
- document settlement exceptions

## Security baseline
- production uses environment-based secrets
- secure cookies and SSL redirect enabled
- version header enforcement enabled
- CI/CD promotion requires gated checks and artifact integrity review
