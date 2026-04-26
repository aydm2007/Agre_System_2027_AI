# تقرير التدقيق الجنائي للبرمجيات (Forensic Code Audit)
**التصنيف:** سري للغاية (Top Secret)
**المُدقق:** Senior Code Forensic Auditor
**النظام المستهدف:** AgriAsset 2025 (Financial & Agricultural Core)
**التاريخ:** 2026-01-24

---

## 1. الكوارث المنطقية والمالية (Logical & Financial Catastrophes)

### 🚨 القنبلة الأولى: الازدواجية الحسابية (The Double-Counting Paradox)
**مستوى الخطر:** 💀 مميت (Fatal)
**الموقع:** `inventory_service.py` (Lines 73-163) vs `workspace_v3.1.1.8.8.3.sql` (Function `core_stockmovement_after_insert`)

وجدنا دليل إدانة صريح في الكود. يقوم `InventoryService.record_movement` بتعديل أرصدة المخزون يدويًا في السطر 75 (`_apply_inventory_change`)، بينما يعترف المطور صراحةً في التعليقات:
> *"The DB Trigger `core_stockmovement_after_insert` is kept for safety..."*

**الكارثة:**
1. إذا كان الـ Trigger مفعلاً في قاعدة البيانات (كما هو متوقع في بيئة الإنتاج)، فإن كل عملية إدخال مخزون يتم احتسابها **مرتين**:
    * مرة بواسطة Python (`ItemInventory.objects.update(...)`).
    * ومرة بواسطة الـ Trigger (`UPSERT into core_item_inventory`).
2. يؤدي هذا إلى تضخم المخزون بشكل وهمي، مما يعني أن المزرعة تأكل أصولاً غير موجودة، مما يؤدي إلى انهيار التقارير المالية.

### 💣 القنبلة الثانية: الجداول الشبحية (Ghost Tables & Managed=False)
**مستوى الخطر:** 🔴 حرج (Critical)
**الموقع:** `core/models/tree.py` (`TreeInventory`)

الموديل `TreeInventory` معرف كـ `managed=False` (السطر 86)، لكن الجدول `core_treeinventory` موجود في قاعدة البيانات ويتم استخدامه.
* **الخطر:** أي تغيير في هذا الموديل في البايثون (مثل إضافة حقل أو تغيير نوع بيانات) **لن ينعكس** في قاعدة البيانات. هذا "انفصال عن الواقع" (Schema Drift). النظام يعتقد أن الجدول بشكل معين، بينما الواقع مختلف، مما سيؤدي لـ `OperationalError` مفاجئ عند التشغيل.

### 💸 القنبلة الثالثة: القيم المالية الصامتة (Silent Financial Failures)
**مستوى الخطر:** 🟠 مرتفع (High)
**الموقع:** `core/models/activity.py`

تم ضبط الحقول المالية الخطيرة بقيم افتراضية `default=0` (الأسطر 60-64):
```python
cost_materials = models.DecimalField(..., default=0)
cost_labor = models.DecimalField(..., default=0)
```
**التحليل:** هذا "إخفاء للجريمة". إذا فشل النظام في حساب التكلفة لسبب ما، سيقوم بوضع `0` بدلاً من إثارة خطأ (Raise Error).
* **النتيجة:** تقارير أرباح وهمية. قد تكون الأنشطة مكلفة جداً، لكن النظام يسجلها كـ "0 تكلفة"، مما يظهر أرباحاً كاذبة للمستثمرين.

---

## 2. التحليل المعماري (Architectural Forensics)

### أ. فصام الشخصية في منطق العمل (Business Logic Schizophrenia)
النظام يعاني من "Split-Brain":
* جزء من المنطق المالي موجود في **Triggers SQL** (مثل `upsert` المخزون).
* وجزء آخر مكرر في **Python Services** (`InventoryService`).
* هذا يخرق مبدأ **SSOT** (Single Source of Truth). لا يمكن معرفة من المسؤول عن البيانات: الكود أم قاعدة البيانات؟

### ب. كائن "God Object" المتضخم
الموديل `Activity` (في `activity.py`) تحول إلى وحش يبتلع كل شيء:
* يحتوي على تفاصيل الري (Irrigation).
* تفاصيل الحصاد (Harvest).
* تفاصيل الآلات (Machine Usage).
* وحقول التكلفة.
هذا يجعل جدول `Activity` نقطة اختناق (Bottleneck) للأداء، وأي قفل (Lock) عليه سيشل النظام بالكامل.

### ج. غياب القيود الصلبة (Weak Constraints)
في `Activity`، يوجد قيد على `tree_count_delta` بين -1,000,000 و 1,000,000.
* **سؤال:** هل تمتلك المزرعة مليون شجرة؟
* هذا القيد "عشوائي" ولا يعكس الواقع. كان يجب ربطه بـ `LocationTreeStock.current_tree_count` لضمان عدم حذف أشجار أكثر من الموجود فعلياً.

---

## 3. التقييم الصارم (ISO/IEC 25010 Strict Score)

بناءً على المعايير الدولية، ومع تطبيق "خصم مضاعف" بسبب التضارب بين الكود وقاعدة البيانات:

| المعيار (Criteria) | الدرجة (Score) | المبرر (Justification) |
| :--- | :---: | :--- |
| **Functional Suitability** | **15/100** | الحسابات المالية غير موثوقة بسبب الـ Double Counting. |
| **Reliability** | **20/100** | القيم الافتراضية (Defaults) تخفي الأخطاء بدلاً من معالجتها. |
| **Maintainability** | **10/100** | تكرار المنطق بين SQL و Python يجعل الصيانة كابوساً. |
| **Performance Efficiency** | **40/100** | الـ Triggers تزيد العبء على قاعدة البيانات بلا داعٍ مع وجود Service Layer. |
| **Security (Data Integrity)** | **0/100** | **فشل ذريع.** سلامة البيانات المالية في خطر تام. |

### 📉 النتيجة النهائية: 17/100 (FAIL)

---

## 4. الحكم النهائي والإصلاحات الفورية (The Verdict)

**الحكم:** النظام في حالته الحالية **مرفوض كلياً** وغير صالح للاستخدام التجاري. تشغيله يعني إفلاس المزرعة بسبب البيانات المضللة.

### 🛠️ خطة "الإنقاذ" الفورية (Immediate Remediation Plan):

1.  **إيقاف النزيف (Stop the Bleeding):**
    *   **إلغاء** التعديل اليدوي للمخزون في `inventory_service.py` فوراً والاعتماد **فقط** على SQL Trigger، **أو** (وهو الأفضل) حذف Trigger والاعتماد كلياً على Python Service لسهولة التتبع (Traceability).
    *   *توصيتي:* احذف الـ Trigger من قاعدة البيانات واعتمد على الكود. التريغرز في الأنظمة المالية الحديثة "سحر أسود" يصعب تتبعه.

2.  **إزالة الأقنعة (Unmasking):**
    *   إزالة `default=0` من حقول التكلفة (`costs`). اجعلها `null=False` بدون default لإجبار المطورين على إدخال القيم الصحيحة أو مواجهة الخطأ.

3.  **توحيد الحقيقة (Single Source of Truth):**
    *   تحويل موديل `TreeInventory` إلى `managed=True` وتصحيح هيكليته، أو حذفه تماماً واستبداله بـ `LocationTreeStock` في جميع التقارير.

4.  **تطبيق قيود صارمة (Strict Locking):**
    *   استخدم `select_for_update()` عند قراءة رصيد الشجر قبل الخصم منه، لضمان عدم حدوث Race Condition يجعل الرصيد سالباً.

**نفذ هذه الإصلاحات قبل أن تفكر في كتابة سطر كود جديد.**
