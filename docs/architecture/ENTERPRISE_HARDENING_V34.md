# Enterprise Hardening v34

## What changed
- Added broker-ready integration publishers (logging, memory, webhook, composite).
- Added integration hub registry and queue snapshot helpers.
- Added `dispatch_outbox` management command for operational dispatch.
- Added optional strict farm-scope guard middleware for mutating API traffic.
- Added diagnostics endpoint for integration hub queue and publisher state.
- Extended observability summary with integration-hub snapshot and tenant-hardening mode.

## Why it matters
This pass moves the project from basic integration readiness to **operator-ready integration discipline**:
- external side effects can be routed by environment,
- queue health is visible via diagnostics,
- tenant intent can be enforced explicitly when the platform operator turns strict mode on.
