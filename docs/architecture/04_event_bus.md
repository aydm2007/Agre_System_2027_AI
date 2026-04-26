
# ⚡ Architecture: AgriEventBus (Decoupled Core)
**Last Updated:** 2026-02-03
**Status:** Live (Phase 3)

## 🎯 Purpose
To decouple the monolithic dependencies between `ActivityService`, `TreeInventoryService`, and `FinancialLedger`.
Previously, deleting an Activity required circular imports to revert stock and financial entries.

## 🏗️ Design Pattern
We utilize the **Observer Pattern** via a custom `AgriEventBus`.
- **Publisher:** `ActivityService` fires events (`ActivityCreated`, `ActivityDeleted`).
- **Subscribers:** Specialized listeners handle side effects.
- **Async Option:** Ready for `Celery` or `Redis` (currently sync for integrity).

## 📡 Event Catalog

### `activity_committed`
Fired when an activity is created or updated.
- **Provider:** `ActivityService`
- **Listeners:**
  - `InventoryListener`: Updates stock (ItemInventory).
  - `CostingListener`: Triggers `calculate_activity_cost`.
  - `LedgerListener`: Writes immutable ledger entries.

### `activity_deleted`
Fired BEFORE an activity is physically deleted.
- **Provider:** `ActivityService`
- **Listeners:**
  - `LedgerListener`: Writes reversal entries (Contra-Entries).
  - `InventoryListener`: Reverts stock changes.

## 🛡️ Integrity Guarantees
- **Transaction Atomicity:** All listeners run within the Publisher's `transaction.atomic()` block.
- **Idempotency:** Listeners usually check for existing records to prevent double-posting.

## 📝 Code Reference
- **Core:** `backend/smart_agri/core/events/bus.py`
- **Events:** `backend/smart_agri/core/events/definitions.py`
- **Listeners:** `backend/smart_agri/core/services/listeners.py`
