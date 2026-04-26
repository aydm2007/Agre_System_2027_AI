-- Seed Data: Yemen Agricultural Seasons
-- Based on local agricultural calendars (Highlands, Tihama, Eastern Plateau)

INSERT INTO public.core_season (name, start_date, end_date, is_active, description, created_at, updated_at) VALUES 
(
    'الموسم الصيفي 2025 (Seif)',
    '2025-05-01',
    '2025-08-31',
    true,
    'موسم الصيف (سيف): مناسب لزراعة الذرة الرفيعة في المرتفعات، والفواكه (المانجو والموز) في تهامة.',
    NOW(),
    NOW()
),
(
    'موسم الخريف 2025 (Rainy Season)',
    '2025-08-01',
    '2025-10-31',
    true,
    'موسم الخريف (الأمطار): الفترة الأهم للزراعة المطرية في إب وتعز والمرتفعات الوسطى. موسم حصاد التمور في حضرموت.',
    NOW(),
    NOW()
),
(
    'الموسم الشتوي 2025/2026',
    '2025-11-01',
    '2026-02-28',
    true,
    'موسم الشتاء: مناسب لزراعة القمح والشعير في المناطق الباردة (المرتفعات الشمالية والوسطى).',
    NOW(),
    NOW()
),
(
    'الموسم الربيعي 2026',
    '2026-03-01',
    '2026-05-31',
    true,
    'موسم الربيع: تحضير الأرض وبداية زراعة الخضروات في المناطق الدافئة.',
    NOW(),
    NOW()
)
ON CONFLICT (id) DO NOTHING;  -- Assuming ID is auto-increment, conflict usually on unique constraints if any. 
-- Since we rely on auto-increment, we just insert. If you run this multiple times, it might duplicate unless we check name.

-- Optional: Clean duplicates if running multiple times (safe approach)
-- DELETE FROM public.core_season a USING public.core_season b WHERE a.id < b.id AND a.name = b.name;
