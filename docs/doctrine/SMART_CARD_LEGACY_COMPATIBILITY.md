# Smart Card Stack Legacy Compatibility Doctrine

## Version Date: 2026-03-24
## Context: AgriAsset V21 (YECO Edition)

### Overview
This document outlines the planned lifecycle for legacy execution fields in the DailyLog payload. With the introduction of the canonical `smart_card_stack` in V21, the system has unified the read-side UI representation of execution metrics.

### The Canonical Contract
For all new and migrated UI surfaces (e.g. `DailyLog`, `Task Execution`), the `smart_card_stack` object array returned inside the `Activity` payload must be the authoritative source for enabling/disabling sections and presenting their current posture to the user.

### Legacy Fields (Compatibility Only)
The following fields remain in the output payload strictly for backward compatibility with old mobile clients and unmodified reports. They must *not* be used to make new business or UI rendering decisions:

1. `plan_metrics`
2. `task_focus`
3. `daily_achievement`
4. `control_metrics`
5. `variance_metrics`
6. `ledger_metrics`
7. `health_flags`

### Deprecation and Removal Strategy
These fields are currently marked `[COMPATIBILITY_ONLY]`. 
A dedicated cleanup phase (post V25) will monitor usage logs. Once zero active clients demand these fields for a consecutive 90-day period, they will be removed from the API serializers.

### Enforcement
Frontend code introducing any new dependency on the legacy fields must be rejected in code review. All frontend logic must consume the `smart_card_stack` array and filter by `card_key` to resolve field-level visibility constraints.
