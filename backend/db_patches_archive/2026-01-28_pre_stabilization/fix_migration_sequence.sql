-- إصلاح خطأ تسلسل معرفات جدول التهجير (تحديث صريح)
-- Fix: duplicate key value violates unique constraint "django_migrations_pkey"
-- تعيين العداد ليبدأ من 100 كما طلبت

SELECT setval(pg_get_serial_sequence('django_migrations', 'id'), 100, true);
