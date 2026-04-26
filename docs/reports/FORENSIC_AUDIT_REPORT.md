# 💀 Forensic Code Audit Report: AgriAsset 2025

**Date:** 2026-01-28
**Auditor:** Agri-Guardian (AI Forensic Unit)
**Target:** Core Financial & Inventory Services (`backend/smart_agri/core/services/`)
**Classification:** **STRICT / CONFIDENTIAL**

---

## 🚨 Section 1: Logical & Financial Disasters (The "Kill Switch" List)

These are not "bugs"; they are potential bankruptcy events waiting to happen.

### 1. The "Free Lunch" Vulnerability (Under-Costing Risk)
*   **File:** `core/services/costing.py` (Lines 31, 41, 46, 55, 74)
*   **The Horror:** The system heavily relies on `COSTING_STRICT_MODE`. If this flag is ever disabled (e.g., by a junior dev trying to "fix" a crash), the system silently returns `Decimal("0")` for missing Labor, Overhead, or Machine rates.
*   **Scenario:** A massive planting operation occurs. The config is missing. Strict mode is off. Result: **The crop is capitalized at $0 cost.** When sold, the P&L shows 100% profit. You pay taxes on phantom profits while bleeding actual cash.
*   **Severity:** **CRITICAL**

### 2. The Nested N+1 Performance Bomb
*   **File:** `core/services/cost_allocation.py` (Lines 147-151)
*   **The Horror:** Inside `allocate_actual_bills`, there is a loop over `active_plans`. Inside that loop, it runs a database query: `plan.activities.filter(...)`.
*   **Math:** If you have 50 Bills to allocate across 100 active Crop Plans, that is `50 * 100 = 5000` database queries in a single transaction.
*   **Scenario:** End-of-month processing hangs indefinitely or times out, locking the `ActualExpense` table and preventing any other financial operations.
*   **Severity:** **HIGH**

### 3. Raw SQL Injection... by the Architects?
*   **File:** `core/services/tree_inventory.py` (Line 328)
*   **The Horror:** `cursor.execute(f"SELECT 1 FROM {table} WHERE id = %s FOR UPDATE", [stock.pk])`
*   **Analysis:** While parameterized, this hardcodes PostgreSQL syntax inside Python logic. It bypasses Django's ORM abstraction layer. If you ever switch DBs or if Django changes how it names tables (unlikely but possible), this breaks.
*   **Fix:** Use `LocationTreeStock.objects.select_for_update().get(pk=stock.pk)`. There is no need for raw SQL here.
*   **Severity:** **MEDIUM (Maintenance Risk)**

---

## 🏗️ Section 2: Architectural Analysis

### 🟢 The Good (Commendable Patterns)
1.  **Immutable Ledger:** `core/models/finance.py` is a fortress. The `save()` method checking `self._state.adding` and raising `ValidationError` on updates is world-class defensive coding. The `row_hash` adds a layer of tamper-evidence.
2.  **Atomic Transactions:** `inventory_service.py` and `tree_inventory.py` correctly use `transaction.atomic` and `select_for_update`. The inventory math explicitly prevents negative stock *before* commiting.
3.  **Deadlock Awareness:** `tree_inventory.py` explicitly sorts lock keys in `bulk_process_activities` (Lines 658, 667). This shows "Senior Engineer" level awareness of database concurrency.

### 🔴 The Bad (Structural Weaknesses)
1.  **Strict Mode Dependency:** The logic is littered with `if COSTING_STRICT_MODE: raise else return 0`. This toggle is dangerous. Financial integrity should **never** be togglable. It should always be strict.
2.  **God Object Tendencies:** `Activity` is central to everything. It links to logs, tasks, locations, inventories, and ledgers. While common in Django, it makes the `Activity` table a hotspot for locking contention.

---

## 📊 Section 3: ISO/IEC 25010 Audit Score

| Characteristic | Score | Penalty Reason |
| :--- | :---: | :--- |
| **Functional Suitability** | **95/100** | Logic is sound and handles edge cases well. |
| **Performance Efficiency** | **65/100** | **-35 Points** for the N+1 Loop in `cost_allocation.py`. |
| **Reliability** | **88/100** | Strong transaction management, but "Silent Failure" risk if strict mode is off. |
| **Security** | **92/100** | Immutable Ledger and explicit RLS checks are excellent. |
| **Maintainability** | **60/100** | **-40 Points** for Raw SQL, complex custom locking logic, and overly verbose service methods. |
| **Portability** | **40/100** | Hardcoded PostgreSQL-specific SQL. |

### **Global Score: 73/100** (Grade: C+)

---

## ⚖️ Section 4: The Verdict & Immediate Executions

The system is **safe but heavy**. It won't lose money due to race conditions (thanks to locking), but it might lie about costs if configuration is missing (due to "Soft Mode") and it will crash under load (due to N+1).

### 🛡️ Mandatory Remediation Plan (Execute Immediately)

1.  **Refactor `allocate_actual_bills`:**
    *   **Action:** Pre-calculate `plan_areas` in a single aggregation query using `CropPlan.objects.annotate(total_planted=Sum('activities__...'))`. Remove the query inside the loop.
2.  **Kill `COSTING_STRICT_MODE`:**
    *   **Action:** Hardcode it to `True`. Remove the `else: return 0` branches. Missing cost data is *always* an error in a financial system.
3.  **Purge Raw SQL:**
    *   **Action:** Replace `cursor.execute` in `tree_inventory.py` with Django's native `.select_for_update()`.

**Status:** PENDING CORRECTION.
**Signed:** *Agri-Guardian*
