-- Add 'data' JSONB column to core_activity for flexible attribute storage
-- Corresponding to Django migration 0045

BEGIN;

DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='core_activity' AND column_name='data') THEN 
        ALTER TABLE core_activity ADD COLUMN data JSONB DEFAULT '{}'::jsonb;
    END IF; 
END $$;

COMMIT;
