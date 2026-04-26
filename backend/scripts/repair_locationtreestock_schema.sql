-- [AGRI-GUARDIAN] Schema Repair: Add missing SoftDeleteModel columns to core_locationtreestock
-- Date: 2026-02-07
-- Issue: LocationTreeStock inherits from SoftDeleteModel but table is missing required columns
-- Run this script with: python manage.py dbshell < scripts/repair_locationtreestock_schema.sql

-- Add is_active column (required by SoftDeleteModel)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'core_locationtreestock' AND column_name = 'is_active') THEN
        ALTER TABLE core_locationtreestock ADD COLUMN is_active BOOLEAN DEFAULT TRUE NOT NULL;
        RAISE NOTICE 'Added is_active column to core_locationtreestock';
    ELSE
        RAISE NOTICE 'is_active column already exists';
    END IF;
END $$;

-- Add deleted_at column (required by SoftDeleteModel)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'core_locationtreestock' AND column_name = 'deleted_at') THEN
        ALTER TABLE core_locationtreestock ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE NULL;
        RAISE NOTICE 'Added deleted_at column to core_locationtreestock';
    ELSE
        RAISE NOTICE 'deleted_at column already exists';
    END IF;
END $$;

-- Add deleted_by_id column (required by SoftDeleteModel)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'core_locationtreestock' AND column_name = 'deleted_by_id') THEN
        ALTER TABLE core_locationtreestock ADD COLUMN deleted_by_id INTEGER NULL;
        -- Add foreign key constraint
        ALTER TABLE core_locationtreestock 
            ADD CONSTRAINT fk_locationtreestock_deleted_by 
            FOREIGN KEY (deleted_by_id) REFERENCES auth_user(id) ON DELETE SET NULL;
        RAISE NOTICE 'Added deleted_by_id column to core_locationtreestock';
    ELSE
        RAISE NOTICE 'deleted_by_id column already exists';
    END IF;
END $$;

-- Create index on is_active for soft delete queries
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_locationtreestock_is_active') THEN
        CREATE INDEX idx_locationtreestock_is_active ON core_locationtreestock(is_active);
        RAISE NOTICE 'Created index on is_active';
    END IF;
END $$;

-- Verify the changes
SELECT column_name, data_type, is_nullable, column_default 
FROM information_schema.columns 
WHERE table_name = 'core_locationtreestock' 
ORDER BY ordinal_position;
