-- ================================================================
-- تحسينات قاعدة البيانات (Database Best Practices Patch) - مصحح
-- ================================================================

DO $$
BEGIN

    -- 1. إضافة الفهرس المركب (Composite Index) للأصول
    -- نتحقق من جدول pg_indexes لمعرفة ما إذا كان الفهرس موجوداً
    IF NOT EXISTS (
        SELECT 1
        FROM pg_indexes
        WHERE schemaname = 'public'
        AND indexname = 'core_activity_asset_scope_idx'
    ) THEN
        CREATE INDEX core_activity_asset_scope_idx
            ON public.core_activity (log_id, asset_id, task_id)
            WHERE (asset_id IS NOT NULL);

        RAISE NOTICE 'تم إنشاء الفهرس core_activity_asset_scope_idx بنجاح.';
    ELSE
        RAISE NOTICE 'الفهرس core_activity_asset_scope_idx موجود مسبقاً.';
    END IF;

    -- 2. إضافة قيد المفتاح الأجنبي (Foreign Key) للأصناف
    -- نتحقق من information_schema لمعرفة ما إذا كان القيد موجوداً
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_name = 'core_activity_variety_id_fk'
        AND table_name = 'core_activity'
    ) THEN
        ALTER TABLE public.core_activity
            ADD CONSTRAINT core_activity_variety_id_fk
            FOREIGN KEY (variety_id)
            REFERENCES public.core_cropvariety (id)
            DEFERRABLE INITIALLY DEFERRED;

        RAISE NOTICE 'تم إضافة قيد المفتاح الأجنبي core_activity_variety_id_fk بنجاح.';
    ELSE
        RAISE NOTICE 'قيد المفتاح الأجنبي core_activity_variety_id_fk موجود مسبقاً.';
    END IF;

END $$;
