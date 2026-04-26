-- ============================================================================
-- DB Patch: Forensic Audit Remediation - Phase 1
-- Version: 0080
-- Date: 2026-01-24
-- Purpose: Fix inventory trigger location support and add safety constraints
-- ============================================================================

-- STEP 1: Fix the stock movement trigger to properly handle location_id
-- ============================================================================
-- Problem: The current trigger ignores location_id and sets it to NULL,
--          causing a mismatch with Python code that expects location-based inventory.

CREATE OR REPLACE FUNCTION public.core_stockmovement_after_insert() 
RETURNS trigger AS $$
BEGIN
    -- Skip if essential fields are missing
    IF NEW.farm_id IS NULL OR NEW.item_id IS NULL THEN
        RETURN NEW;
    END IF;

    -- Upsert into core_item_inventory with location support
    -- Uses (farm_id, item_id, location_id) as the composite key
    INSERT INTO public.core_item_inventory (farm_id, location_id, item_id, qty, uom, updated_at)
    VALUES (
        NEW.farm_id, 
        NEW.location_id,  -- FIX: Now preserving the actual location_id
        NEW.item_id, 
        NEW.qty_delta, 
        COALESCE(NEW.uom, ''), 
        CURRENT_TIMESTAMP
    )
    ON CONFLICT (farm_id, item_id) WHERE location_id IS NULL
    DO UPDATE SET 
        qty = public.core_item_inventory.qty + EXCLUDED.qty,
        updated_at = EXCLUDED.updated_at;

    -- Handle location-specific inventory separately
    IF NEW.location_id IS NOT NULL THEN
        INSERT INTO public.core_item_inventory (farm_id, location_id, item_id, qty, uom, updated_at)
        VALUES (
            NEW.farm_id, 
            NEW.location_id, 
            NEW.item_id, 
            NEW.qty_delta, 
            COALESCE(NEW.uom, ''), 
            CURRENT_TIMESTAMP
        )
        ON CONFLICT (farm_id, location_id, item_id)
        DO UPDATE SET 
            qty = public.core_item_inventory.qty + EXCLUDED.qty,
            updated_at = EXCLUDED.updated_at;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION public.core_stockmovement_after_insert() 
IS 'Forensic Audit Fix (2026-01-24): Now properly handles location_id for per-location inventory tracking.';


-- STEP 2: Add CHECK constraint for non-negative inventory
-- ============================================================================
-- Note: This constraint may already exist from Django model definition.
-- Using IF NOT EXISTS pattern via exception handling.

DO $$
BEGIN
    ALTER TABLE public.core_item_inventory 
    ADD CONSTRAINT iteminventory_qty_check CHECK (qty >= 0);
EXCEPTION 
    WHEN duplicate_object THEN 
        RAISE NOTICE 'Constraint iteminventory_qty_check already exists, skipping.';
END $$;


-- STEP 3: Add CHECK constraint for stock movement delta (not zero)
-- ============================================================================

DO $$
BEGIN
    ALTER TABLE public.core_stockmovement 
    ADD CONSTRAINT stockmovement_delta_not_zero CHECK (qty_delta <> 0);
EXCEPTION 
    WHEN duplicate_object THEN 
        RAISE NOTICE 'Constraint stockmovement_delta_not_zero already exists, skipping.';
END $$;


-- STEP 4: Create missing managed=False tables
-- ============================================================================

-- 4.1: TreeLossReason
CREATE TABLE IF NOT EXISTS public.core_treelossreason (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(150) NOT NULL,
    name_ar VARCHAR(150),
    description TEXT DEFAULT ''
);

COMMENT ON TABLE public.core_treelossreason 
IS 'Lookup table for tree loss reasons. Created by Forensic Audit Remediation 2026-01-24.';


-- 4.2: TreeProductivityStatus  
CREATE TABLE IF NOT EXISTS public.core_treeproductivitystatus (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(150) NOT NULL,
    name_ar VARCHAR(150),
    sort_order INTEGER DEFAULT 0,
    color VARCHAR(20) DEFAULT '#6c757d'
);

COMMENT ON TABLE public.core_treeproductivitystatus 
IS 'Lookup table for tree productivity statuses (juvenile, productive, declining). Created by Forensic Audit Remediation 2026-01-24.';

-- Seed default productivity statuses
INSERT INTO public.core_treeproductivitystatus (code, name, name_ar, sort_order, color)
VALUES 
    ('juvenile', 'Juvenile', 'ناشئة', 1, '#17a2b8'),
    ('productive', 'Productive', 'منتجة', 2, '#28a745'),
    ('declining', 'Declining', 'متراجعة', 3, '#ffc107'),
    ('dormant', 'Dormant', 'خاملة', 4, '#6c757d')
ON CONFLICT (code) DO NOTHING;


-- 4.3: TreeInventory (if needed as separate from LocationTreeStock)
-- Note: LocationTreeStock is the main table; TreeInventory may be a legacy/view

-- 4.4: Ensure unique constraint exists for location-based inventory
DO $$
BEGIN
    ALTER TABLE public.core_item_inventory 
    ADD CONSTRAINT iteminventory_farm_location_item_uc 
    UNIQUE (farm_id, location_id, item_id);
EXCEPTION 
    WHEN duplicate_object THEN 
        RAISE NOTICE 'Constraint iteminventory_farm_location_item_uc already exists, skipping.';
END $$;


-- STEP 5: Add indexes for performance
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_item_inventory_farm_item 
ON public.core_item_inventory (farm_id, item_id);

CREATE INDEX IF NOT EXISTS idx_item_inventory_location 
ON public.core_item_inventory (location_id) 
WHERE location_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_stockmovement_farm_item 
ON public.core_stockmovement (farm_id, item_id);


-- ============================================================================
-- END OF PATCH
-- ============================================================================
