# Architecture Documentation

## Overview
This document outlines the architectural changes introduced to modularize the `smart_agri` backend, improving maintainability and scalability.

## 1. Modular Models
The monolithic `models.py` has been decomposed into a `models/` package (`smart_agri/core/models/`). This separation groups related domain models into specific modules:

| Module | Description | Key Models |
| :--- | :--- | :--- |
| `base.py` | Shared base classes | `SoftDeleteModel`, `Status` |
| `farm.py` | Farm configuration | `Farm`, `Location`, `Asset` |
| `crop.py` | Crop management | `Crop`, `CropVariety`, `CropProduct` |
| `activity.py` | Operational activities | `Activity` and its extensions (`ActivityHarvest`, `ActivityIrrigation`...) |
| `inventory.py` | Stock & Inventory | `Item`, `ItemInventory`, `StockMovement`, `HarvestLot` |
| `planning.py` | Seasonal planning | `CropPlan`, `CropTemplate`, `Season` |
| `log.py` | Logging & Auditing | `DailyLog`, `AuditLog` |
| `tree.py` | Tree lifecycle | `TreeInventory`, `TreeProductivityStatus` |

**Imports**: All models are exposed via `smart_agri.core.models.__init__.py`, maintaining backward compatibility for most imports.

## 2. Service Layer Pattern
We have introduced a Service Layer pattern to encapsulate complex business logic, ensuring a "Fat Model, Thin View" or "Service-based" approach where consistency is critical.

### Key Services
*   **`ActivityItemService`**: Centralizes logic for adding/removing items from activities. It guarantees that any change to activity items triggers a full cost recalculation for the activity.
*   **`InventoryService`**: Standardizes how stock movements are recorded. It provides methods to query stock levels and ensures the integrity of the inventory ledger.
*   **`TreeInventoryService`**: Handles the complex logic of tree counts, additions, and removals based on activities.

## 3. Data Integrity & Signals
*   **Strict Consistency**: Services use `transaction.atomic` to ensure operations are all-or-nothing.
*   **Signals**: Logic that must happen on DB mutations (like inventory updates from stock movements) is preserved in `models/inventory.py` signals or encapsulated within Services.

## 4. API Layer
The API layer (`api/`) has also been refactored to separate Serializers (`api/serializers/`) and ViewSets (`api/viewsets/`), improving navigation and reducing file sizes.
