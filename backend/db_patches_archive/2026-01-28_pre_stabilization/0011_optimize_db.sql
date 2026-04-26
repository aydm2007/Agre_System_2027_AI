-- Database Optimization & Missing Fields Patch

-- 1. Add missing 'status' field to CropPlan (Required for Dashboard)
ALTER TABLE public.core_cropplan ADD COLUMN IF NOT EXISTS "status" varchar(20) DEFAULT 'active' NOT NULL;

-- 2. Add Indexes for Performance (Dashboard & Reports)
-- CropPlan
CREATE INDEX IF NOT EXISTS core_cropplan_status_idx ON public.core_cropplan (status);
CREATE INDEX IF NOT EXISTS core_cropplan_deleted_at_idx ON public.core_cropplan (deleted_at);

-- Sale
CREATE INDEX IF NOT EXISTS sales_sale_deleted_at_idx ON public.sales_sale (deleted_at);
CREATE INDEX IF NOT EXISTS sales_sale_status_date_idx ON public.sales_sale (status, sale_date);

-- Season (ensure index exists)
CREATE INDEX IF NOT EXISTS core_season_is_active_idx ON public.core_season (is_active);
