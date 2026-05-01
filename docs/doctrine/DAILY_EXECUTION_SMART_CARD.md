# Daily Execution Smart Card Doctrine

## Purpose

Define the canonical contract for the smart card embedded in `DailyLog` and keep this workflow independent from QR.

## Canonical Flow

`CropPlan -> DailyLog -> Activity -> Smart Card Stack -> Control -> Variance -> Ledger`

- `CropPlan` is the planning source of truth.
- `Activity` is the operational source of truth.
- The smart card stack is read-side only.
- Financial posting originates from backend activity processing, not from the card UI.
- One `Activity` remains linked to one `Task`; multi-card behavior is derived from the task contract, not from multiple transactional tasks.

## Card Contract

The workflow keeps the legacy summary fields for compatibility:

- `plan_metrics`
- `task_focus`
- `daily_achievement`
- `control_metrics`
- `variance_metrics`
- `ledger_metrics`
- `health_flags`

The canonical read-side contract is:

- `smart_card_stack`

Each `smart_card_stack` entry must expose:

- `card_key`
- `title`
- `enabled`
- `order`
- `mode_visibility`
- `status`
- `metrics`
- `flags`
- `data_source`
- `policy`
- `source_refs`

The stack is derived from `Activity.task_contract_snapshot` first, with fallback to the live
`Task.task_contract` only for legacy activities missing a valid snapshot.

Task creation may begin from an `archetype` or crop-specific preset, but the persisted contract
must be an explicit `task_contract` that can enable multiple smart cards inside one task.

## Standard Card Keys

- `execution`
- `materials`
- `labor`
- `well`
- `machinery`
- `fuel`
- `perennial`
- `harvest`
- `control`
- `variance`
- `financial_trace`

`SIMPLE` renders the cards exposed by `presentation.simple_preview`.

`STRICT` renders the cards exposed by `presentation.strict_preview`, including governed financial trace where policy allows.

Farm policy remains part of the execution contract:

- `FarmSettings.show_daily_log_smart_card=false` hides smart-card UI in `DailyLog` even when the task contract is smart-card capable.
- `FarmSettings.show_daily_log_smart_card=true` does not force every card to appear; rendering still depends on the effective task contract and execution context.
- `FarmSettings.allow_creator_self_variance_approval` may permit creator self-approval of a critical variance only. It never authorizes creator self-approval of the final daily log.
- For perennial tasks spanning multiple locations, `service_counts` rows must carry their own `location_id`. Variety union and coverage labels help selection, but final submission remains row-location-specific.
- `DailyLog` write-side must normalize `effective_task_contract` into a task-aware entry context. The same contract governs visible sections, labor rules, perennial rules, and submit-time payload scrubbing.
- Labor entry in `DailyLog` is task-contract-aware. If the `labor` card is disabled, the labor step becomes non-operative and stale labor payload fields must be removed before submit.
- When a `DailyLog` is linked to a `Supervisor`, material consumption must resolve from that supervisor's accepted `Custody` location only. Field execution must not deduct directly from the main warehouse or from an `In-Transit` lane.
- Custody issue, acceptance, rejection, and return remain governed inventory workflows outside the smart-card read model. The smart card may reflect posture, but it is not the authoring surface for custody settlement.
- Material authoring in `DailyLog` must consume canonical unit selection only. Free-text `uom`
  values may remain as legacy read compatibility, but they must not remain on the active write path
  for material or harvest entry.
- Activity material lines may split `qty` into `applied_qty` and `waste_qty`. Only `applied_qty` is capitalizable into operational or biological cost; `waste_qty` must remain a separate operating-loss bucket.
- Multi-location perennial service rows may carry optional `distribution_mode` and `distribution_factor` for analytical weighting. This affects execution analytics only and must not create a second posting engine.

## Read-Side Guarantees

- The stack must not create, mutate, approve, or settle ledger rows.
- Costing remains backend-only.
- The stack must not fork the posting engine or the truth chain between `SIMPLE` and `STRICT`.
- Compatibility fields may remain temporarily for older UI surfaces, but new frontend work must consume `smart_card_stack`.
- `DailyLog` and `ServiceCards` are the canonical frontend consumers of this contract and must stay stack-first for modern payloads.
- `/daily-log/harvest` is a discoverability alias that preloads harvest-oriented context but still
  resolves into the same `DailyLog` smart-card contract and the same backend truth chain.
- `/crops/:id/tasks` must behave as `preset + smart-card customization`, not as an `archetype`-only picker.

## Non-QR Rule

- This workflow must function fully through manual field entry.
- QR may remain optional elsewhere in the system, but it is outside this contract.
- Weak-network replay for daily execution must use an append-only atomic envelope (`log + activity + items + service_counts + client metadata`) rather than a split create-then-attach mutation chain.
- Offline daily execution now follows a two-layer contract:
  - `daily_log_drafts`: persistent local draft sessions keyed by `farm + date + draft_uuid`
  - `daily_log_queue`: immutable replay envelopes keyed by their own sync `uuid`
- The authoritative local-draft identity is `farm_id + log_date + draft_uuid`. `created_at` is an
  ordering timestamp only and must not replace `log_date` when restoring the latest matching draft.
- Returning to `DailyLog` without internet must reopen the most recent matching local draft rather than a single global scratch pad.
- Multiple offline submissions for the same day are valid. Each replay envelope may target the same `DailyLog.log_date`, but it must append one activity atomically and must not overwrite a newer queued activity.
- Offline lookup usage is allowed with warning when cached datasets are stale. The UI must expose freshness posture; the backend remains the final authority on reconnect.
- Restored drafts must hydrate canonical foreign-key fields before lookup reconciliation, especially:
  `asset_id`, `item_id`, `well_id`, `product_id`, and `serviceRows[].varietyId`.

## Tree Loss Separation

- Positive `tree_count_delta` is an operational addition or reconciliation event.
- Positive `tree_count_delta` may open a new variety-location execution path for perennial `service_counts` rows when the row is otherwise crop-valid.
- Negative `tree_count_delta` inside `DailyLog` is descriptive operational evidence that must generate variance and managerial trace.
- Routine negative deltas must not directly perform capital impairment.
- Direct entry of the current perennial balance is not a `DailyLog` action. Opening or recount corrections to `LocationTreeStock.current_tree_count` must use the audited tree-inventory administrative adjustment path, while `DailyLog` remains delta-only.
- Extraordinary biological disasters must move into Axis 18 `Mass Casualty Write-off`.

## Perennial Variety Location Rule

- Perennial/tree-oriented daily execution must not fetch varieties by crop alone when execution locations are known.
- Write-side perennial variety options must remain `crop-scoped` to the active `DailyLog.crop`. Rows with `crop_id=null` or a different crop may remain legacy read context, but they are not valid write authority.
- For one selected location, the frontend should receive the varieties available in that location.
- For multiple selected locations, the frontend should receive the union of available varieties with `location_ids` and `available_in_all_locations`.
- Perennial statistics in `DailyLog` and the summary strip in `tree-census` must reconcile against the same current operational balance: `LocationTreeStock.current_tree_count`. `BiologicalAssetCohort` alive totals remain cohort-structure context and should surface as reconciliation evidence, not replace the current balance.
- Tree-census and tree-inventory surfaces may expose a governed administrative action to register the physical current balance for a location-variety pair. This path must require an explicit reason, produce `TreeStockEvent.ADJUSTMENT`, and leave append-only audit evidence.
- The union rule is operationally preferred to an intersection rule, but the UI must disclose coverage clearly so the operator understands whether a variety is available in all selected locations or only some of them.

## Correction Rule

- Activity edits must reconcile operational state.
- Financial corrections must use reversal plus re-posting.
- Silent overwrite of historical economic meaning is forbidden.

## Release Evidence

When this workflow changes, require:

```bash
python backend/manage.py test smart_agri.core.tests.test_service_cards smart_agri.core.tests.test_daily_log_tree_api smart_agri.core.tests.test_tree_inventory_service smart_agri.core.tests.test_tree_inventory_sync smart_agri.core.tests.test_tree_variance smart_agri.core.tests.test_tree_census_service --keepdb --noinput
npm --prefix frontend run test -- src/components/daily-log/__tests__/DailyLogSmartCard.test.jsx src/pages/__tests__/ServiceCards.test.jsx --run
set PLAYWRIGHT_ARTIFACT_ROOT=%TEMP%\\agriasset-pw-smart-card
npx --prefix frontend playwright test frontend/tests/e2e/daily-log-smart-card.spec.js --project=chromium --config=frontend/playwright.config.js --workers=1 --reporter=line
```

Supplemental readiness may also attach an expanded SIMPLE proof bundle for mixed seasonal/perennial execution and mode-isolation checks. This bundle is supporting readiness evidence only; it does not replace the canonical score authority of `verify_axis_complete_v21`.
