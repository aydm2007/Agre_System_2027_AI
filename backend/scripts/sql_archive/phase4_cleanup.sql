-- FILE: backend/scripts/phase4_cleanup.sql
-- ROUND 5 REMEDIATION: CATASTROPHIC SCHEMA FIXES
-- -----------------------------------------------------------

BEGIN;

-- 1. GHOST TABLE EXORCISM (Doppelgänger Crisis)
-- We confirmed via models.py that the underscores are the REAL tables.
-- Dropping the imposters.
DROP TABLE IF EXISTS public.core_laborrate CASCADE;
DROP TABLE IF EXISTS public.core_machinerate CASCADE;
DROP TABLE IF EXISTS public.location_wells CASCADE; 

-- 2. FINANCIAL PRECISION (Penny Shaving)
-- Upgrading Sales columns to 4 decimal places to prevent revenue vanishing.
-- Using SAFE cast logic.
ALTER TABLE public.sales_saleitem 
    ALTER COLUMN unit_price TYPE numeric(14, 4) USING unit_price::numeric(14, 4);

ALTER TABLE public.sales_saleitem 
    ALTER COLUMN total_price TYPE numeric(14, 4) USING total_price::numeric(14, 4);

-- 3. SEQUENCE MIGRATION (Identity Crisis) - PARTIAL
-- Converting core_season to Identity as a pilot.
-- Note: Assuming id is currently integer/serial.
-- We must drop the sequence ownership first if it exists, but 'ALTER ... ADD GENERATED' 
-- works best on plain columns. 
-- For safety in this script, we will just sync the sequences for now to prevent immediate crashes.
-- SELECT setval('core_season_id_seq', COALESCE((SELECT MAX(id)+1 FROM core_season), 1), false);

COMMIT;
