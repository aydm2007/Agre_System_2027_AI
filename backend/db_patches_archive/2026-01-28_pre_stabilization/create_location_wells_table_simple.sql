-- إنشاء جدول ربط المواقع بالآبار (علاقة كثير لكثير)
CREATE TABLE IF NOT EXISTS public.location_wells (
    id SERIAL PRIMARY KEY,
    location_id BIGINT NOT NULL REFERENCES public.core_location(id) ON DELETE CASCADE,
    asset_id BIGINT NOT NULL REFERENCES public.core_asset(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(location_id, asset_id)
);

-- إنشاء فهرس لتحسين الأداء
CREATE INDEX IF NOT EXISTS idx_location_wells_location_id ON public.location_wells(location_id);
CREATE INDEX IF NOT EXISTS idx_location_wells_asset_id ON public.location_wells(asset_id);
