-- Tree Service Coverage support (PostgreSQL 16)
-- Creates table to store per-activity service counts for perennial trees.
BEGIN;

CREATE TABLE IF NOT EXISTS public.core_treeservicecoverage (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ NULL,
    service_count INTEGER NOT NULL CHECK (service_count >= 0),
    service_type VARCHAR(40) NOT NULL DEFAULT 'general' CHECK (service_type IN ('general','irrigation','fertilization','pruning')),
    total_before INTEGER NULL,
    total_after INTEGER NULL,
    notes TEXT NOT NULL DEFAULT '',
    activity_id BIGINT NOT NULL REFERENCES public.core_activity(id) ON DELETE CASCADE,
    location_id BIGINT NOT NULL REFERENCES public.core_location(id) ON DELETE CASCADE,
    crop_variety_id BIGINT NOT NULL REFERENCES public.core_cropvariety(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS core_treeservicecoverage_activity_idx
    ON public.core_treeservicecoverage (activity_id);

CREATE INDEX IF NOT EXISTS core_treeservicecoverage_location_variety_idx
    ON public.core_treeservicecoverage (location_id, crop_variety_id);

COMMIT;
