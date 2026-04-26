-- Cleanup script for Saradud Agriculture
-- يحذف جميع سجلات اليومي (core_dailylog) وجميع الحركات التابعة لها (core_activity)
-- بالإضافة إلى الجداول المتسلسلة المرتبطة بها.
--
-- ملاحظات الاستخدام:
--   * نفّذ هذا الملف من خلال pgAdmin 4 أو أي عميل PostgreSQL مع صلاحيات مشرف.
--   * يتم تشغيله داخل معاملة واحدة بحيث يمكن التراجع في حال حدوث خطأ.

BEGIN;

SET LOCAL search_path TO public;

-- حذف كل الأنشطة المرتبطة بالسجل اليومي (سيقوم ON DELETE CASCADE بإزالة التفاصيل الفرعية).
DELETE FROM core_activity
WHERE log_id IN (SELECT id FROM core_dailylog);

-- حذف جميع سجلات اليومي بعد تنظيف الأنشطة التابعة لها.
DELETE FROM core_dailylog;

-- إعادة ضبط عدادات الترقيم (Sequences) للجداول المرتبطة لضمان تسلسل صحيح بعد التنظيف.
SELECT setval('public.core_activity_id_seq', COALESCE(MAX(id), 0) + 1, false) FROM public.core_activity;
SELECT setval('public.core_activity_item_id_seq', COALESCE(MAX(id), 0) + 1, false) FROM public.core_activity_item;
SELECT setval('public.core_activityitem_id_seq', COALESCE(MAX(id), 0) + 1, false) FROM public.core_activityitem;
SELECT setval('public.core_service_coverage_id_seq', COALESCE(MAX(id), 0) + 1, false) FROM public.core_service_coverage;
SELECT setval('public.core_treeservicecoverage_id_seq', COALESCE(MAX(id), 0) + 1, false) FROM public.core_treeservicecoverage;
SELECT setval('public.core_dailylog_id_seq', COALESCE(MAX(id), 0) + 1, false) FROM public.core_dailylog;

COMMIT;

