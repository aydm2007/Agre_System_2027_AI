
# تعليمات تطبيق الإصلاحات

## 1. إصلاح نموذج TreeServiceCoverage

تم إنشاء ملف ترحيل جديد `0015_fix_tree_service_coverage_fields.py` لإضافة الحقول المفقودة إلى نموذج TreeServiceCoverage. لتطبيق هذا الإصلاح:

```bash
python manage.py migrate
```

## 2. إصلاح مشكلة الترميز في ملف الإعدادات

تم إنشاء ملف إعدادات جديد `settings_fixed.py` يحل مشكلة الترميز في وصف API. لاستبدال الملف الأصلي:

```bash
mv smart_agri/settings.py smart_agri/settings_original.py
mv smart_agri/settings_fixed.py smart_agri/settings.py
```

## 3. إصلاح مشكلة raise بدون تحديد نوع الاستثناء

تم إصلاح مشكلة raise بدون تحديد نوع الاستثناء في ملف `tree_inventory.py`. تم تحديث الملف مباشرة.

## 4. إنشاء مجلد السجلات

تم إنشاء مجلد `logs` لحل مشكلة تسجيل الأخطاء. المجلد جاهز للاستخدام.

## 5. تحسين ملف API

تم إنشاء ملف API محسّن `api_optimized.py` يحل مشكلة الحجم الكبير للملف الأصلي. لاستبدال الملف الأصلي:

```bash
mv smart_agri/core/api.py smart_agri/core/api_original.py
mv smart_agri/core/api_optimized.py smart_agri/core/api.py
```

## 6. إعادة تشغيل الخادم

بعد تطبيق جميع الإصلاحات، أعد تشغيل الخادم:

```bash
python manage.py runserver
```

## ملاحظات هامة

- قبل تطبيق أي تغييرات، قم بإنشاء نسخة احتياطية من قاعدة البيانات
- بعد تطبيق الترحيلات، تحقق من أن قاعدة البيانات تعمل بشكل صحيح
- في حالة وجود أي مشاكل، يمكنك العودة إلى الملفات الأصلية التي تم حفظها باسم `_original.py`
