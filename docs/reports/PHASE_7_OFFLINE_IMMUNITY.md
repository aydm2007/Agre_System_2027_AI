# Phase 7 — Offline Immunity (Idempotency V2)

**Scope:** Ensure retry-safe behavior under weak networks with deterministic idempotent responses.

## What’s Implemented
- Server-side idempotency records persist response status/body for replay on duplicate requests.
- Mutation endpoints enforce `X-Idempotency-Key` and return deterministic responses on retries.
- Fiscal year rollover (`POST /fiscal-years/{id}/rollover/`) is enforced as idempotent with cache-and-replay semantics inside `transaction.atomic()`.

## Operational Requirements
- Clients must generate a UUID per mutation request and reuse it on retries.
- Duplicate requests should return cached success or explicit `409` without side effects.

## Follow-ups
- Verify offline queue replays use the same idempotency key per mutation.
- Attach replay test evidence before release.
