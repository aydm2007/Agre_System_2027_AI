-- FILE: backend/scripts/phase2_architectural_cleanup.sql
-- ARCHITECTURAL CLEANUP V1 (STRICT ISO/IEC 25010 COMPLIANCE)
-- -----------------------------------------------------------

BEGIN;

-- 1. KILL THE DUPLICATE (Split-Brain Resolution)
-- This table 'core_iteminventory' (no underscores) is a legacy ghost.
-- The real table is 'core_item_inventory' (with underscore) managed by InventoryService.
DROP TABLE IF EXISTS public.core_iteminventory CASCADE;

-- 2. REMOVE SAFETY NETS (Strict Financial Integrity)
-- Removing DEFAULT 0 forces the application to explicitly calculate costs.
-- If the application fails to calculate, the transaction MUST fail (Safety by Crashing).
ALTER TABLE public.core_activity ALTER COLUMN cost_materials DROP DEFAULT;
ALTER TABLE public.core_activity ALTER COLUMN cost_labor DROP DEFAULT;
ALTER TABLE public.core_activity ALTER COLUMN cost_machinery DROP DEFAULT;
ALTER TABLE public.core_activity ALTER COLUMN cost_overhead DROP DEFAULT;
ALTER TABLE public.core_activity ALTER COLUMN cost_total DROP DEFAULT;

-- 3. NORMALIZE GOD OBJECT (SSOT Enforcement)
-- These fields exist in sub-tables (core_activity_irrigation, etc.).
-- Removing them from the parent table prevents data divergence.
ALTER TABLE public.core_activity DROP COLUMN IF EXISTS well_reading;
ALTER TABLE public.core_activity DROP COLUMN IF EXISTS machine_meter_reading;
ALTER TABLE public.core_activity DROP COLUMN IF EXISTS planted_area;
ALTER TABLE public.core_activity DROP COLUMN IF EXISTS planted_uom;
ALTER TABLE public.core_activity DROP COLUMN IF EXISTS planted_area_m2;

COMMIT;

-- VERIFICATION NOTE:
-- After this runs, any Code that tries to read 'well_reading' from core_activity will crash.
-- This is INTENTIONAL. It forces the use of core_activity_irrigation.
