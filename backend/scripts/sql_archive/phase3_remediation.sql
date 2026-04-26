-- FILE: backend/scripts/phase3_remediation.sql
-- ROUND 4 REMEDIATION: STRICT INDEXING & SECURITY
-- -----------------------------------------------------------

BEGIN;

-- 1. PRIMARY MATERIAL ILLUSION (Fixing Race Condition)
-- Remove any existing weak index if present (optional check)
-- DROP INDEX IF EXISTS unique_primary_crop_material;

-- Create Partial Unique Index
-- Only one "is_primary=True" allowed per crop per active record.
CREATE UNIQUE INDEX IF NOT EXISTS unique_primary_crop_material 
ON public.core_cropmaterial (crop_id) 
WHERE is_primary = true AND deleted_at IS NULL;


-- 2. DISK-FILLER LEAK (Cleanup Policy Enhancement - DB Level)
-- Optional: If we wanted to solve it in DB, we could use pg_cron (if available).
-- Since we implemented a Python Command, we will just ensure the index exists for fast deletion.
CREATE INDEX IF NOT EXISTS idx_idempotency_created_at ON public.core_idempotencyrecord (created_at);

COMMIT;
