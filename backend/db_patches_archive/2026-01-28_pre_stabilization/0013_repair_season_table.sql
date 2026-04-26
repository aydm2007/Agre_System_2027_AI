-- Repair Script for 'core_season' Table
-- Fixes error: column "is_active" does not exist

-- 1. Safely add missing columns if they don't exist
ALTER TABLE public.core_season ADD COLUMN IF NOT EXISTS is_active boolean NOT NULL DEFAULT true;
ALTER TABLE public.core_season ADD COLUMN IF NOT EXISTS description text NOT NULL DEFAULT '';
ALTER TABLE public.core_season ADD COLUMN IF NOT EXISTS start_date date;
ALTER TABLE public.core_season ADD COLUMN IF NOT EXISTS end_date date;
ALTER TABLE public.core_season ADD COLUMN IF NOT EXISTS deleted_at timestamp with time zone;

-- 2. Create the index for performance
CREATE INDEX IF NOT EXISTS core_season_is_active_idx ON public.core_season (is_active);

-- 3. Insert default season (only if table is empty)
INSERT INTO public.core_season (name, start_date, end_date, is_active, description, created_at, updated_at)
SELECT 'الموسم الحالي 2025', '2025-01-01', '2025-12-31', true, 'تم إنشاؤه تلقائيًا لاستكمال النظام', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM public.core_season);
