# مخطط جرد الأشجار المعمّرة

يوضح هذا المستند المحدث كيف يدعم النظام الحالي إدارة الأشجار المعمّرة، بما يشمل خدمة العدد الخدمي (الأعداد التي تمت خدمتها فعلياً في نشاط معين) وآليات المزامنة بين الواجهة الخلفية والواجهة الأمامية.

## 1. خدمة TreeInventoryService

### المسؤوليات الأساسية
- مراقبة جدول `core_locationtreestock` وتحديث الرصيد الحالي لكل صنف داخل موقع محدد بعد أي نشاط زراعي.
- إنشاء سجل في `core_treestockevent` لكل تغيير فعلي (غرس/فقد/حصاد/تصحيح) مع حفظ بيانات المستخدم، التاريخ، السبب، والقياسات (مياه، سماد، إلخ).
- ضمان سلامة البيانات عبر المعاملات الذرّية (`transaction.atomic`) واستخدام الأقفال (`select_for_update`) منعاً لحدوث سباقات تحديث على نفس الرصيد.

### واجهة الخدمة (مقترحة)
```python
class TreeInventoryService:
    def reconcile_activity(
        *,
        activity,
        user=None,
        delta_change=None,
        previous_delta=None,
        activity_tree_count_change=None,
        previous_activity_tree_count=None,
        previous_location=None,
        previous_variety=None,
    ) -> TreeInventoryResult | None:
        ...

    def manual_adjustment(
        *,
        location_stock,
        delta,
        reason,
        metadata,
    ) -> TreeStockEvent:
        ...

    def refresh_productivity_status(
        *,
        queryset,
        batch_size=200,
        as_of=None,
    ) -> dict:
        ...
```

## 2. العدد الخدمي (Tree Service Coverage)

### الهدف
العدد الخدمي هو عدد الأشجار التي تمت خدمتها فعلياً (مثل ري أو تسميد) خلال نشاط معين، حتى لو لم يتغير الرصيد الفعلي للأشجار. هذا يسمح بإعداد تقارير دقيقة عن التغطية التشغيلية.

### مخطط البيانات
يثبت جدول `core_treeservicecoverage` المعلومات التالية:

| الحقل              | الوصف |
|--------------------|-------|
| `activity_id`      | النشاط المرتبط بالعدد الخدمي. |
| `location_id`      | الموقع الذي تمت فيه الخدمة. |
| `crop_variety_id`  | الصنف (المحصول الفرعي) الذي تمت خدمته. |
| `service_count`    | عدد الأشجار المخدومة. |
| `service_type`     | نوع الخدمة (`general`, `irrigation`, `fertilization`, `pruning`). |
| `total_before`     | الرصيد قبل الخدمة (اختياري). |
| `total_after`      | الرصيد بعد الخدمة (اختياري). |
| `notes`            | ملاحظات إضافية. |

تمت إضافة الجدول عبر سكربت SQL جاهز (`db_patches/2025-10-26_tree_service_coverage.sql`) بحيث يمكن تطبيقه مباشرة على PostgreSQL 16.

#### Service scope alignment (October 2025 update)
- Daily log submissions now persist both service_type and service_scope, ensuring each coverage row carries the operational scope (irrigation, fertilisation, pruning, cleaning, protection). Missing values are normalised to general for backward compatibility.
- Offline queue payloads (idb-keyval and IndexedDB) are normalised on enqueue/read so legacy cached items receive a valid service_scope before they are replayed or restored from the queue panel.
- IndexedDB (SaradudAgriDB) was bumped to version 2 to rewrite stored serviceCounts arrays with the same normalised scope values, keeping historical snapshots consistent with Django migrations.

### كيف يتم التحديث؟
- عند إرسال نشاط أشجار معمرة من الواجهة الأمامية، يتم تمرير مصفوفة `service_counts_payload` مع كل صف يحتوي على (`location_id`, `variety_id`, `service_count`, `service_type`, `total_before`, `total_after`, `notes`).
- يقوم `ActivitySerializer` في الواجهة الخلفية بإنشاء السجلات المرتبطة أو تحديثها (وحذف السجلات السابقة إن وجدت) لضمان التزامن التام مع النشاط.
- عند إدخال النشاط في وضع عدم الاتصال، يتم تخزين البيانات كاملة في صف الانتظار وإعادة إرسالها فور توفر الاتصال مع الحفاظ على idempotency.

## 3. واجهة الإنجاز اليومي (DailyLog)

### لوحة الأشجار المعمّرة
عند اختيار مهمة موسومة بحقل `is_perennial_procedure` (إجراء الأشجار المعمرة) في نموذج `Task`، يظهر قسم خاص يعرض:
- مجموعة الأصناف المرتبطة بالموقع والرصيد الحالي لكل صنف.
- حقول إدخال للأعداد الخدمية، نوع الخدمة، الرصيد قبل/بعد، والملاحظات.
- إمكانية إضافة صنف يدوي (مع صلاحيات مناسبة) في حال عدم ظهوره في الجرد.
- مؤشرات تنبيه عند تجاوز العدد الخدمي للرصيد أو عند نقص البيانات الضرورية.

> **ملاحظة**: لا يزال الحقل القديم `requires_tree_count` مدعوماً لأغراض التوافق الخلفي، لكن الحقل الجديد `is_perennial_procedure` هو المرجع الرئيسي لتفعيل واجهة الأشجار المعمّرة في السجل اليومي والتقارير.

### الربط بالـ API
- يتم استدعاء `TreeInventory.summary` لجلب بيانات الموقع والصنف (مع خيار تعطيل تحديث حالة الإنتاجية لتقليل التكلفة).
- بعد حفظ النشاط، يتم عرض رسالة نجاح تتضمن الرصيد السابق والجديد (إن تغير).

## 4. خطوات التطبيق على قاعدة البيانات

1. افتح PgAdmin 4 أو استخدم `psql`.
2. نفّذ محتوى الملف `db_patches/2025-10-26_tree_service_coverage.sql`:
   ```sql
   \i db_patches/2025-10-26_tree_service_coverage.sql
   ```
   أو قم بنسخ محتوى الملف ولصقه داخل محرر الاستعلام.
3. تأكد من نجاح الأمر ووجود الجدول والفهارس باستخدام:
   ```sql
   \d+ core_treeservicecoverage;
   ```

## 5. اختبارات مقترحة

- **اختبارات وحدات للواجهة الخلفية**:
  - حفظ نشاط مع `service_counts_payload` يجب أن ينشئ سجلات مرتبطة صحيحة.
  - تعديل النشاط يجب أن يحذف السجلات القديمة ويضيف الجديدة.
  - حذف النشاط يجب أن يحذف السجلات المرتبطة (Cascade).

- **اختبارات واجهة (Vitest/RTL)**:
  - عرض اللوحة عند تفعيل مؤشر الأشجار المعمرة.
  - إدخال أكثر من صنف والتأكد من إرسال `service_counts_payload`.
  - تشغيل نفس السيناريو في وضع عدم الاتصال والتأكد من تخزين المصفوفة في طوابير IndexedDB.

## 6. نقاط مرجعية

- **الواجهة الخلفية**:
  - النموذج: `backend/smart_agri/core/models.py` (نموذج `TreeServiceCoverage`).
  - نموذج المهمة: `backend/smart_agri/core/models.py` (الحقل `Task.is_perennial_procedure`).
  - Serializer: `ActivitySerializer` داخل `backend/smart_agri/core/api.py`.
  - خدمة الجرد: `backend/smart_agri/core/services/tree_inventory.py`.

- **الواجهة الأمامية**:
  - صفحة الإدخال: `frontend/src/pages/DailyLog.jsx`.
  - عميل API: `frontend/src/api/client.js` (تأكد من إرسال `service_counts_payload`).

- **ملف SQL**:
  - `db_patches/2025-10-26_tree_service_coverage.sql`.

باتباع هذه التحديثات، تصبح عملية إدارة الأشجار المعمرة أكثر دقة، مع فصل واضح بين الرصيد الفعلي (الجرد) والعدادات الخدمية اليومية، مما يتيح تقارير تشغيلية وقرارات صيانة أفضل. 
