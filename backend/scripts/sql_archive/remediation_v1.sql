-- FORENSIC REMEDIATION V1: DESTROY DOUBLE COUNTING MECHANISM
-- ----------------------------------------------------------------
-- Objective: Remove 'core_stockmovement_after_insert_tr' trigger.
-- Reason: It conflicts with inventory_service.py causing double inventory updates.
-- Authority: Senior Forensic Auditor
-- ----------------------------------------------------------------

BEGIN;

-- 1. Drop the specific trigger causing double counting
DROP TRIGGER IF EXISTS core_stockmovement_after_insert_tr ON core_stockmovement;

-- 2. Drop the associated function if it exists (Cleanup)
DROP FUNCTION IF EXISTS core_stockmovement_after_insert_func();

-- 3. (Optional) Drop other potential legacy triggers mentioned in audit
DROP TRIGGER IF EXISTS core_locationtreestock_touch ON core_treeservicecoverage;
DROP FUNCTION IF EXISTS core_locationtreestock_touch_func();

COMMIT;

-- VERIFICATION:
-- Ensure that inserting into core_stockmovement NO LONGER updates core_item_inventory automatically.
