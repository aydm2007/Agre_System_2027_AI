-- Tree service coverage enhancements for PostgreSQL 16 / pgAdmin
-- Aligns manual DB patch with Django migration 0013_remove_treeservicecoverage_core_treeser_location_f0c262_idx_and_more

BEGIN;

-- 1. Add new columns (idempotent guards for repeated runs)
ALTER TABLE public.core_service_coverage
    ADD COLUMN IF NOT EXISTS service_scope character varying(40) NOT NULL DEFAULT 'general',
    ADD COLUMN IF NOT EXISTS source_log_id bigint;

-- 2. Ensure existing rows carry the default value in case column existed without data
UPDATE public.core_service_coverage
SET service_scope = 'general'
WHERE service_scope IS NULL;

-- Align legacy rows: if scope remains generic but type is specific, mirror the service_type
UPDATE public.core_service_coverage
SET service_scope = service_type
WHERE service_type IS NOT NULL
  AND service_type <> 'general'
  AND service_scope = 'general';

-- 3. Establish foreign key to daily logs (ON DELETE SET NULL matches ORM behaviour)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'core_service_coverag_source_log_id_fk'
    ) THEN
        ALTER TABLE public.core_service_coverage
            ADD CONSTRAINT core_service_coverag_source_log_id_fk
            FOREIGN KEY (source_log_id)
            REFERENCES public.core_dailylog(id)
            ON DELETE SET NULL;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- 4. Refresh legacy indexes to match new naming and scope coverage
DROP INDEX IF EXISTS public.core_treeser_location_f0c262_idx;
ALTER INDEX IF EXISTS public.core_treeser_activity_9a5aa2_idx RENAME TO core_servic_activit_8c4742_idx;
ALTER INDEX IF EXISTS public.core_tree_serv_recorded_idx RENAME TO core_servic_recorde_7ffecd_idx;

CREATE INDEX IF NOT EXISTS core_servic_activit_d5ddc6_idx
    ON public.core_service_coverage (activity_id, service_scope);

CREATE INDEX IF NOT EXISTS core_servic_locatio_8ea372_idx
    ON public.core_service_coverage (location_id, crop_variety_id, service_scope);

ALTER TABLE public.core_service_coverage
    DROP CONSTRAINT IF EXISTS core_service_coverage_unique_active;
DROP INDEX IF EXISTS public.core_service_coverage_unique_active;
CREATE UNIQUE INDEX core_service_coverage_unique_active
    ON public.core_service_coverage (activity_id, crop_variety_id, service_scope)
    WHERE deleted_at IS NULL;

COMMIT;
