/* FORENSIC AUDIT: FINAL ZERO-ERROR CHECK 
   Date: 2026-01-24
   Target: AgriAsset2025 Database
   
   IF THIS RETURNS ANY ROWS, THE AUDIT FAILS.
*/

-- CHECK 1: Negative Inventory (The Cardinal Sin)
SELECT 'FAIL: Negative Inventory Detected' as issue, id, qty 
FROM core_iteminventory 
WHERE qty < 0;

-- CHECK 2: Ledger Mismatch (Split-Brain Check)
-- Sum of all movements MUST equal current inventory snapshot
SELECT 'FAIL: Ledger vs Inventory Mismatch' as issue, 
       i.item_id, i.qty as snapshot_qty, m.ledger_sum
FROM core_iteminventory i
JOIN (
    SELECT item_id, farm_id, COALESCE(location_id, -1) as loc_id, SUM(qty_delta) as ledger_sum
    FROM core_stockmovement
    GROUP BY item_id, farm_id, location_id
) m ON i.item_id = m.item_id 
   AND i.farm_id = m.farm_id 
   AND COALESCE(i.location_id, -1) = m.loc_id
WHERE ABS(i.qty - m.ledger_sum) > 0.0001; -- Allow tiny floating point epsilon if any

-- CHECK 3: Financial Integrity (Cost Totals)
-- Total Cost MUST equal sum of its components
SELECT 'FAIL: Cost Sum Mismatch' as issue, id, cost_total
FROM core_activity
WHERE ABS(cost_total - (cost_materials + cost_labor + cost_machinery + cost_overhead)) > 0.01;

-- CHECK 4: Strict Mode Violations (Zero Cost Activities)
-- In strict mode, labor shouldn't be 0 if hours > 0
SELECT 'FAIL: Suspicious Zero Labor Cost' as issue, id 
FROM core_activity
WHERE hours > 0 AND cost_labor = 0 AND deleted_at IS NULL;
