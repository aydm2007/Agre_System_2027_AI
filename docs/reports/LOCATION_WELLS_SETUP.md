# إعداد جدول ربط المواقع بالآبار

## المشكلة
لا تعمل صفحة إدارة ربط المواقع بالآبار (http://localhost:5173/location-wells) بسبب عدم إنشاء جدول `location_wells` أو عدم تطبيق ترحيلاته بعد. الواجهة البرمجية (Model + ViewSet) مدمجة مسبقًا ضمن تطبيق `smart_agri.core`، لذلك لا نحتاج إلى تطوير API جديدة بل إلى تفعيل المكونات الحالية والتأكد من جاهزية قاعدة البيانات.

## الحل

### 1. إنشاء الجدول في قاعدة البيانات
قم بتنفيذ ملف `db_patches/create_location_wells_table_simple.sql` في قاعدة البيانات PostgreSQL:

```sql
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
```

### 2. استخدام الواجهة المدمجة في الخادم
- يتضمن تطبيق `smart_agri.core` النموذج `LocationWell` داخل الملف `backend/smart_agri/core/models.py`، كما يوفر الـ Serializer والـ ViewSet الجاهزين في `backend/smart_agri/core/api.py`، ويتم تسجيل المسار `/api/v1/location-wells/` عبر الـ router الموجود في نهاية الملف نفسه.
- تأكد من أن التطبيق مفعّل من خلال وجود السطر `"smart_agri.core"` داخل قائمة `INSTALLED_APPS` في `backend/smart_agri/settings.py`. إذا كان السطر مفقودًا، أضفه ثم أعد تشغيل الخادم.
- راجع حالة الترحيلات قبل تشغيلها باستخدام:

  ```bash
  python manage.py showmigrations smart_agri.core | grep location_well
  ```

  إذا ظهر أن الترحيل `0005_location_well` غير مطبق (علامة غير موجودة)، عندها فقط نفّذ الأمر:

  ```bash
  python manage.py migrate smart_agri.core
  ```

  أما إذا كان الترحيل مطبقًا مسبقًا فليس هناك حاجة لتشغيله مجددًا.

### 3. اختبار الواجهة
بعد التأكد من جاهزية الجدول والواجهة المدمجة، يمكنك اختبار الواجهة عن طريق:
1. الدخول إلى http://localhost:5173/location-wells
2. اختيار مزرعة من القائمة
3. اختيار موقع وبئر وإنشاء رابط بينهما
4. التحقق من أن الرابط تم إنشاؤه بنجاح

## ملاحظات
- العلاقة بين المواقع والآبار هي علاقة كثير لكثير (Many-to-Many)
- يمكن ربط بئر واحد بعدة مواقع
- يمكن ربط موقع واحد بعدة آبار
- تم تحديث واجهة المستخدم لتوضيح هذه العلاقة

**يرجى إجراء مراجعة تقنية للتوثيق بعد تطبيق الخطوات أعلاه للتأكد من دقة المحتوى واستمراريته.**
