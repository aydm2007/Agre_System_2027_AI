# تقرير تشخيص الإقلاع (Dev Boot Diagnosis)

التاريخ: 2026-02-27 01:03:40 -08:00
الهدف: تشخيص سبب عدم اكتمال تشغيل بيئة التطوير محليًا.

## Baseline قبل الإصلاح

1. `cmd /c start_dev_stack.bat check`  
   النتيجة: PASS
   - `System check identified no issues (0 silenced).`
   - `No planned migration operations.`

2. `python backend/manage.py check`  
   النتيجة: PASS

3. `npm --prefix frontend run build`  
   النتيجة: FAIL
   - الخطأ الحرج:
     - `EPERM: operation not permitted, open '...\\frontend\\dist\\sw.js'`
   - السياق: الفشل أثناء `vite-plugin-pwa` عند توليد `sw.js`.

## فحوصات ACL

1. `whoami`  
   - `sultanyahya\ibrahim`

2. محاولة منح صلاحيات:
   - `icacls frontend\dist /grant "sultanyahya\ibrahim:(OI)(CI)M" /T`
   - `icacls backend\staticfiles /grant "sultanyahya\ibrahim:(OI)(CI)M" /T`
   - النتيجة: `Access is denied`

3. محاولة حذف/تعديل ملفات داخل `dist/staticfiles`:
   - النتيجة: `Access is denied` على ملفات متعددة.

## السبب الجذري

- ملفات build artifacts الحالية مملوكة/مقفلة بصلاحيات تمنع المستخدم الحالي من الكتابة/الاستبدال.
- هذا يمنع `vite build` (PWA service worker write) ويؤثر على التنظيف الكامل.

## الأثر

- **تشغيل Dev Runtime** غير متأثر (يمكن تشغيل `runserver` + `vite dev`).
- **بناء Production محليًا** متأثر (يفشل حتى يتم فتح ACL أو حذف artifacts بصلاحية أعلى).

