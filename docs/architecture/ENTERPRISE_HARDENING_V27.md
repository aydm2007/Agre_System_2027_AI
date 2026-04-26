# Enterprise Hardening v27

## What was improved

### 1. Frontend API modularization continued
The former monolithic `frontend/src/api/client.js` was reduced further by extracting two dedicated modules:

- `frontend/src/api/offlineQueueStore.js`
- `frontend/src/api/tokenStorage.js`

This separates:
- offline queue persistence
- queue summarization and ordering
- scoped owner-aware key resolution
- auth token local storage operations

### 2. Event architecture hardening
`backend/smart_agri/core/events.py` now uses a shared transactional dispatcher so both event styles:

- named signal-based events (`AgriEventBus`)
- typed legacy domain events (`EventBus`)

follow the same commit-aware dispatch path.

Additional improvements:
- duplicate typed subscriber registration is prevented
- `reset()` support added to both buses for safer tests and more deterministic startup behavior
- named event publication logging was normalized and simplified

### 3. Test coverage extended
A new test module was added:

- `backend/smart_agri/core/tests/test_named_event_bus.py`

It verifies:
- named events do not leak on rollback
- immediate publish mode works when explicitly requested

The legacy atomic event tests were also hardened by clearing subscribers between runs.

## Impact

This pass does not complete the road to 100/100, but it materially improves:

- modularity
- event consistency
- transaction safety
- test determinism
- maintainability of the frontend integration layer

## Remaining priorities

1. Split `frontend/src/api/client.js` further into domain clients
2. Break down oversized backend services
3. Replace broad exception handling in scripts and runtime edges
4. Add deeper telemetry and SLO-ready observability
5. Tighten bounded context separation inside `core`
