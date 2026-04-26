# Offline Outbox and Replay Contract

AgriAsset is designed for weak-network and remote-site operation. The offline contract is no longer a generic `safeRequest()` wrapper. The canonical implementation is a Dexie-backed split between:

- resumable local drafts for `DailyLog`
- immutable queued submissions for replay
- explicit failed and `dead_letter` handling when the server rejects a payload

This document is a readable public guide for the active offline contract. Product truth and governance truth remain governed by the active doctrine and `AGENTS.md`.

## Canonical offline model

The active queues are stored in `frontend/src/offline/dexie_db.js`.

Transactional queues:

- `generic_queue`
- `sales_queue`
- `harvest_queue`
- `daily_log_queue`
- `custody_queue`

Local resumable work:

- `daily_log_drafts`

Read cache only:

- `lookup_cache`

`lookup_cache` is not a transactional replay path. It is a freshness-aware read helper used when the device is offline or the network is unstable.

## Drafts versus queued submissions

`DailyLog` uses a two-layer model:

1. `daily_log_drafts`
   - local, resumable work in progress
   - one draft can be reopened later from the same page
   - the user may start a new operation without overwriting the previous local work

2. `daily_log_queue`
   - immutable replay envelopes
   - each offline submit becomes a separate queued item
   - the queue entry keeps its own `uuid`, `idempotency_key`, `client_seq`, `draft_uuid`, and replay metadata

Submitting offline must never silently mutate the open draft into a generic pending blob. The draft remains a local work record, while the queue entry becomes the replay contract.

## Replay orchestrator

The active orchestrator is `flushQueue()` in `frontend/src/api/client.js`.

- `flushQueue()` is the only replay engine that processes:
  - `generic_queue`
  - `sales_queue`
  - `harvest_queue`
  - `daily_log_queue`
  - `custody_queue`
- `SyncManager` is a trigger wrapper only.
- service worker sync and `online` events may trigger replay, but they do not define a second replay engine.

This means replay behavior should be documented and diagnosed in terms of `flushQueue()`, not older helper names.

## Deterministic replay guarantees

The active `DailyLog` replay contract is enforced by the backend atomic replay view:

- `uuid`
- `idempotency_key`
- `client_seq`
- `device_id`
- `draft_uuid`
- `lookup_snapshot_version`
- `task_contract_snapshot`

Replay is atomic and server-authoritative:

- server state wins conflicts
- out-of-order replay may be rejected
- rejected payloads move to `dead_letter` or `SyncConflict_DLQ`
- the client must surface the reason instead of silently dropping the item

## Queue states

The UI and docs should use the same normalized vocabulary:

- `draft`
- `queued`
- `syncing`
- `failed`
- `dead_letter`

Meaning:

- `draft`: local work not yet submitted to replay
- `queued`: accepted into a replay queue and waiting for sync
- `syncing`: currently being replayed
- `failed`: temporary failure that may be retried
- `dead_letter`: requires operator review or correction before retry

## Freshness posture

Offline work is allowed against cached lookups when needed, but the system must expose freshness clearly.

Expected freshness posture:

- `حديثة`
- `قديمة لكن قابلة للاستخدام`
- `قديمة وتتطلب مراجعة عند المزامنة`

The system does not block field work merely because the device is temporarily offline. Instead:

- cached lookups remain usable
- stale policy context must be flagged
- replay may reject stale or incompatible payloads

## Remote-site policy overlay

`Remote Site` is not the offline switch.

Offline execution is a technical continuity contract.

`remote_site=true` and `weekly_remote_review_required=true` are governance overlays that mean:

- daily execution may continue
- weak-network or delayed sync is expected
- some governed strict-finance actions may remain restricted until the required remote review is recorded

Remote review policy must not block `DailyLog` entry itself.

## Queue-specific notes

### `daily_log_queue`

- canonical queue for offline daily execution replay
- supports resumable drafts through `draft_uuid`
- supports multiple offline submissions for the same day when the user records multiple operations

### `harvest_queue`

- stores offline harvest submissions
- remains part of the same replay orchestration and diagnostics surface

### `custody_queue`

- stores offline supervisor-custody acceptance, rejection, and return actions
- custody consumption still obeys accepted-balance-only rules when replayed

### `generic_queue`

- stores supported non-financial generic offline mutations
- must remain separate from finance-governed posting paths

### `sales_queue`

- remains a documented compatibility transactional queue in the current implementation
- it is included in replay counts and diagnostics
- it is not the preferred model for new offline business workflows
- future cleanup may converge or retire it, but it must not remain undocumented while active in code

## Troubleshooting

If a queued item does not sync:

1. inspect the queue item status in the offline center
2. read `last_error` or the DLQ reason
3. restore the relevant draft or reopen the affected workflow
4. correct the business conflict if needed
5. retry replay

Typical failure classes:

- lookup mismatch after reconnect
- out-of-order replay
- custody balance mismatch
- validation failure after policy or task-contract changes

## Source anchors

Frontend:

- `frontend/src/offline/dexie_db.js`
- `frontend/src/hooks/useDailyLogOffline.js`
- `frontend/src/api/client.js`
- `frontend/src/offline/SyncManager.js`
- `frontend/src/components/offline/OfflineQueuePanel.jsx`

Backend:

- `backend/smart_agri/core/api/viewsets/offline_replay.py`

Doctrine:

- `docs/doctrine/DUAL_MODE_OPERATIONAL_CYCLES.md`
- `docs/doctrine/DAILY_EXECUTION_SMART_CARD.md`
- `docs/doctrine/MULTI_SITE_OFFLINE_OPERATIONS_V6.md`
