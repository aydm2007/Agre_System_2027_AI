-- =============================================================================
-- FINAL REMEDIATION: PURGE LEGACY ARTIFACTS & ENFORCE ULTRA-STRICT INTEGRITY
-- =============================================================================
-- This script removes "Ghost Tables" that cause para-logical redundancy 
-- and hardens constraints for financial/stock events.

BEGIN;

-- 1. PURGE REDUNDANT TABLES (Schizophrenic Logic Prevention)
-- These tables exist in the dump but are not managed by current Python Models.
-- WARNING: These are presumed dead-weight legacies.
DROP TABLE IF EXISTS public.core_iteminventory CASCADE;
DROP TABLE IF EXISTS public.core_iteminventorybatch CASCADE;
DROP TABLE IF EXISTS public.core_laborrate CASCADE;
DROP TABLE IF EXISTS public.core_machinerate CASCADE;
DROP TABLE IF EXISTS public.core_activity_item CASCADE; -- Conflicting with core_activityitem

-- 2. HARDEN TREE STOCK EVENTS
-- Prevent silent $0 or 0-quantity operations which are logically invalid.
ALTER TABLE public.core_treestockevent 
ADD CONSTRAINT trg_treestockevent_delta_nonzero 
CHECK (tree_count_delta <> 0 OR water_volume > 0 OR fertilizer_quantity > 0 OR harvest_quantity > 0 OR event_type = 'inspection');

-- 3. RESOLVE REDUNDANT CONSTRAINTS
ALTER TABLE public.core_locationtreestock DROP CONSTRAINT IF EXISTS core_locationtreestock_tree_count_check;
-- Keeping 'check_stock_positive' as the primary guardian.

-- 4. ENFORCE HARVEST INTEGRITY
ALTER TABLE public.core_activity_harvest ALTER COLUMN harvest_quantity SET NOT NULL;
ALTER TABLE public.core_activity_harvest ALTER COLUMN uom SET NOT NULL;

-- 5. PURGE CONTENT TYPES (Cleanup Registry)
DELETE FROM public.django_content_type WHERE model IN ('iteminventory', 'iteminventorybatch', 'laborrate', 'machinerate', 'activity_item');

COMMIT;
