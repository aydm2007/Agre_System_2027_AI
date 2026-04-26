-- AgriAsset Forensic Patch: Offline Conflict Resolution
-- Target: Critical Operational Tables
-- Rationale: Enable "Last Write Wins" based on device time, not server receive time.

BEGIN;

-- 1. Inventory Sync Support
ALTER TABLE core_iteminventory
ADD COLUMN IF NOT EXISTS device_last_modified_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS sync_version BIGINT DEFAULT 1;

-- 2. Expense Sync Support
ALTER TABLE core_actual_expense
ADD COLUMN IF NOT EXISTS device_created_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS local_device_id VARCHAR(64);

-- Index for fast sync filtering
CREATE INDEX IF NOT EXISTS idx_inventory_device_time 
ON core_iteminventory (device_last_modified_at);

COMMIT;
