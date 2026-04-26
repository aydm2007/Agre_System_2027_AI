-- Performance Indexes for AgriAsset2025

CREATE INDEX IF NOT EXISTS idx_labor_rate_farm_date 
    ON core_labor_rate (farm_id, effective_date DESC)
    WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_treestockevent_activity 
    ON core_treestockevent (activity_id)
    WHERE activity_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_activity_log_active 
    ON core_activity (log_id)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_treeservicecoverage_activity_variety 
    ON core_treeservicecoverage (activity_id, crop_variety_id, location_id);

CREATE INDEX IF NOT EXISTS idx_cropplan_status_active 
    ON core_cropplan (status, farm_id)
    WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS core_costconfiguration (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE,
    farm_id BIGINT NOT NULL UNIQUE REFERENCES core_farm(id) ON DELETE CASCADE,
    overhead_rate_per_hectare NUMERIC(12, 2) NOT NULL DEFAULT 50.00,
    currency VARCHAR(8) NOT NULL DEFAULT 'YER',
    effective_date DATE NOT NULL DEFAULT CURRENT_DATE
);
