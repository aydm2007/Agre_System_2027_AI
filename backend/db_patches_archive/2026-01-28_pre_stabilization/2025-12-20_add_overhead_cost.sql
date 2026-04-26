ALTER TABLE core_activity ADD COLUMN cost_overhead numeric(12, 2) DEFAULT 0 NOT NULL;
ALTER TABLE core_activitycostsnapshot ADD COLUMN cost_overhead numeric(14, 2) DEFAULT 0 NOT NULL;
