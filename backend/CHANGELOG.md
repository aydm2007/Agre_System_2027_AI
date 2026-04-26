## Unreleased

### Phase 4: Hardening Business Operations
- **Feature:** Finalized full lifecycle integration maps for Petty Cash tracking WIP entries from raw logs to finalized settlements (`M4.1`).
- **Feature:** Enforced operational doctrine splitting Sharecropping physical inventory collection from corporate financial settlements (`M4.2`).
- **Feature:** Segregated normal DailyLog tree mortality limits from Mass-Casualty explicit workflows generating IAS-41 impairments (`M4.3`).
- **Feature:** Confirmed strict verification pipelines for Supplier Settlement idempotency controls (`M4.4`).
- **Feature:** Established Fixed Asset mode barriers routing tracking-only behaviors separately from GL capitalization functions (`M4.5`).
- **Feature:** Refined strict reconciliation logic masking cache transfers under SIMPLE Treasury routing (`M4.6`, `M4.7`).
- **Feature:** Asserted Fiscal Period sector review chains barring unauthorized localized manipulation of ledger closing timelines (`M4.8`).

### Phase 3: Sealing SIMPLE/STRICT Boundaries
- **Feature:** Enforced block stopping all unauthorized backend financial and administrative modifications outside of STRICT modes (`M3.1`, `M3.2`).
- **Feature:** Architecturally validated Shadow Accounting chains enabling technical execution without visual numeric leaks (`M3.3`, `M3.6`).
- **Feature:** Sealed component and dashboard routers against leakage; only status summaries and metric burn-rates are exposed safely (`M3.4`).
- **Feature:** Extended the `mode_policy_service.py` ruleset to intercept non-authoritative operations across all modules (`M3.5`).
- **Feature:** Deployed a strict Verification script scanning for hardcoded secrets or trailing wildcard allowed hosts (`M3.7`).
- **Docs:** Synchronized Phase 3 integration testing to traceability components and Readiness Matrices (`M3.8`).

### Phase 2: Strengthening Governance & Sector Approval Chain
- **Feature:** Implemented full suite of 5 Sector Approval Lanes confirming logic separation and escalation rules (`M2.1`).
- **Feature:** Expanded `RoleWorkbench` snapshot tests to verify aggregation and overdue counters for all sector governance lanes + FFM (`M2.2`, `M2.9`).
- **Feature:** Hard-coded compensating controls for SMALL farms enforcing limits and remote review escalation (`M2.3`).
- **Feature:** Blocked MEDIUM and LARGE farms from processing approvals without a mandated Farm Finance Manager (`M2.4`).
- **Feature:** Verified `ApprovalStageEvent` timeline for forensic ledger trail tracking (`M2.5`).
- **Feature:** Blocked Creator Self-Approval across the ecosystem allowing exception bypass only via variance policy (`M2.6`).
- **Feature:** Applied profiled posting authority assertions to the 6 core enterprise financial actions (`M2.7`).
- **Feature:** Restored functional separation between `Farm Chief Accountant` and `Sector Chief Accountant` (`M2.8`).

### Phase 1: Deepening Canonical Smart Card Stack
- **Feature:** Deepened `smart_card_stack_service.py` to become the canonical source of truth for execution card UI presentation and behavior constraints (`M1.1`).
- **Feature:** Tied `ActivitySerializer` to dynamically serve the canonical `smart_card_stack` directly inside `DailyLog` payloads (`M1.2`).
- **Test:** Added `test_smart_card_stack_contract.py` to enforce the 11 required payload criteria and legacy fallback logic (`M1.3`).
- **Docs:** Introduced `SMART_CARD_LEGACY_COMPATIBILITY.md` outlining the deprecation procedure for the `[COMPATIBILITY_ONLY]` fields (`M1.4`, `M1.6`).
- **Refactor:** Removed stray SQLite databases to enforce PostgreSQL-only verification (`M0.1`).
- **Refactor:** Archived bloated and legacy evaluation reports to `docs/archive/legacy_reports/` (`M0.2`).
- **Refactor:** Cleaned up ~50 scratch python scripts, test scripts, and log files from the repository root (`M0.3`, `M0.4`).
- **Refactor:** Updated `.gitignore` to prevent future tracking of generated reports, logs, and frontend build artifacts (`M0.5`).
- **Refactor:** Removed stray `{crop.name}` directory from the backend (`M0.6`).
- **Docs:** Verified `SKILLS_CANONICALIZATION_V21.yaml` and implementation gaps documentation (`M0.7`, `M0.8`).

- Fix: make tree inventory reverse/delete robust when DB FOR UPDATE over joins fails.
  - Use a raw SELECT ... FOR UPDATE against the `location_tree_stock` table to lock
    the row when possible, with a safe fallback if the DB refuses the lock.
  - When reversing an activity would make stock negative, clamp the stock to 0
    and log a warning so the UI/ops can review.
