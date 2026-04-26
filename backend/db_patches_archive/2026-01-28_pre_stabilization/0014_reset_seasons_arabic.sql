-- Reset Seasons to Arabic Only
-- 1. Clears existing seasons to remove English/Mixed duplicates.
-- 2. Inserts strict Arabic agricultural seasons.

-- Disable trigger or constraints if necessary (usually not needed for simple deletes unless FKs exist)
-- We use CASCADE to detach them from existing plans (setting them to null if set up that way, or we might need to be careful).
-- CropPlan has season_ref SET_NULL, so it is safe to delete.

DELETE FROM public.core_season;

INSERT INTO public.core_season (name, start_date, end_date, is_active, description, created_at, updated_at) VALUES 
(
    'الموسم الشتوي',
    '2025-11-01',
    '2026-02-28',
    true,
    'موسم زراعة القمح والشعير في المرتفعات.',
    NOW(),
    NOW()
),
(
    'الموسم الصيفي (سيف)',
    '2025-05-01',
    '2025-08-31',
    true,
    'موسم الفواكه والذرة الرفيعة.',
    NOW(),
    NOW()
),
(
    'موسم الخريف (ممطر)',
    '2025-08-01',
    '2025-10-31',
    true,
    'موسم الزراعة المطرية في إب وتعز.',
    NOW(),
    NOW()
),
(
    'الموسم الربيعي',
    '2026-03-01',
    '2026-05-31',
    true,
    'موسم تحضير الأرض وبداية الخضروات.',
    NOW(),
    NOW()
);
