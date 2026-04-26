
# Enterprise Breakthrough v32

## What changed
- Added `smart_agri.integration_hub` as a dedicated platform capability.
- Introduced canonical event contracts for farm, activity, inventory, and finance domains.
- Added an outbox dispatcher abstraction to separate transactional writes from external effects.
- Added readiness endpoint: `/api/health/integration-hub/`.
- Added baseline connectors for weather, IoT telemetry, and market price enrichment.

## Why it matters
This is the first step from ERP-only architecture toward an agricultural platform architecture. It creates a stable contract for future Kafka, webhook, ETL, and AI integrations without forcing a premature microservices split.
