-- الملف: backend/scripts/phase1_kill_trigger.sql

BEGIN;
-- إزالة التريغر القاتل فوراً
-- Note: Checking both potential naming conventions found in the dump and previous audits
DROP TRIGGER IF EXISTS core_stockmovement_after_insert ON public.core_stockmovement;
DROP TRIGGER IF EXISTS core_stockmovement_after_insert_tr ON public.core_stockmovement;

DROP FUNCTION IF EXISTS public.core_stockmovement_after_insert();
DROP FUNCTION IF EXISTS public.core_stockmovement_after_insert_func();

-- تنظيف أي مخلفات (اختياري ولكن مفضل)
COMMENT ON TABLE public.core_item_inventory IS 'Managed by Python InventoryService (SSOT).';

COMMIT;
