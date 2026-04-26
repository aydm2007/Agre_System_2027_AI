# دليل المطور - AgriAsset V21

> Reference class: public developer guide.
> Canonical format: HTML/MkDocs.
> Word status: derived delivery copy only; never edit Word as source of truth.
> This guide is a curated implementation map. Product truth remains governed by `PRD V21`, `AGENTS.md`, doctrine, and latest canonical evidence.

هذا الدليل موجّه للمطورين والمهندسين الذين يعملون داخل هذا المستودع. هدفه تقليل وقت onboarding وإعطاء خريطة تنفيذ واضحة من دون استبدال المرجع الحاكم.

## 1. من أين تبدأ؟

ابدأ دائمًا بهذا الترتيب:

1. `AGENTS.md`
2. `docs/prd/AGRIASSET_V21_MASTER_PRD_AR.md`
3. `docs/reference/REFERENCE_PRECEDENCE_AND_OVERRIDE_V21.md`
4. `.agent/skills/agri_guardian/SKILL.md`
5. doctrine ذات الصلة
6. latest canonical evidence

### قاعدة حاكمة

أي claim عالٍ مثل `100/100` يجب أن يعود إلى:

- `docs/evidence/closure/latest/verify_axis_complete_v21/summary.*`

## 2. المرجع والأولوية

المستودع يعمل وفق طبقات مرجعية واضحة:

- `PRD V21`: حقيقة المنتج
- `AGENTS.md`: حقيقة التنفيذ والبروتوكول
- doctrine/reference aids: تفسير وتنزيل تشغيلي
- skills: عدسات تنفيذ فقط

### ما الذي لا يجوز؟

- لا يجوز أن تتفوق skill على `AGENTS.md`
- لا يجوز أن يصبح runbook مصدر حقيقة أعلى من PRD أو latest evidence
- لا يجوز أن توصف وثيقة تاريخية كأنها baseline حي

## 3. السلسلة الحاكمة للحقيقة

السلسلة الأساسية:

`CropPlan -> DailyLog -> Activity -> Smart Card Stack -> Control -> Variance -> Ledger`

المعاني:

- `CropPlan`: مصدر التخطيط
- `Activity`: مصدر الحقيقة التشغيلية
- `smart_card_stack`: read-side only
- posting والتكلفة: backend-owned

### نتائج هندسية

- لا تكتب الواجهة قيودًا مباشرة
- لا تنشئ write path ثانيًا إذا كان المسار الأساسي قائمًا
- لا تحوّل smart card إلى transaction engine

## 4. البنية الأمامية

### صفحات محورية

- `Dashboard`
- `SimpleOperationsHub`
- `DailyLog`
- `DailyLogHarvestLaunch`
- `CustodyWorkspace`
- `Reports`
- `Finance`

### قواعد البنية

- `SIMPLE` و`STRICT` يختلفان في السطح، لا في الحقيقة الخلفية
- `DailyLog` هو write path canonical للتنفيذ
- `/daily-log/harvest` alias فقط
- `/inventory/custody` طبقة UI فوق نفس custody APIs
- `/reports` قراءة/توليد فقط
- `SimpleOperationsHub` سطح orchestration front-end فقط، لا business engine جديد

### الوضع العربي وRTL

- الواجهات يجب أن تبقى Arabic-first
- الهوية المعروضة يجب أن تفضل الاسم العربي
- لا تجعل `username` أو `slug` أو codename الواجهة الأساسية للمستخدم

## 5. البنية الخلفية

### قواعد لا تفاوض فيها

- service layer only
- لا `float()` في المال والمخزون
- PostgreSQL only
- farm isolation دائمًا
- append-only ledger
- explicit exceptions only

### وحدات حرجة

- daily execution
- custody transfer services
- offline replay
- reporting support
- finance approvals and governed posting

### ما الذي يجب أن يبقى backend-owned؟

- costing
- posting
- replay atomicity
- policy enforcement
- maker-checker and sector approval behavior

## 6. عقدة `SIMPLE/STRICT`

### `SIMPLE`

- surface فني وتشغيلي
- variance and control posture
- shadow accounting read posture
- لا ERP authoring كامل

### `STRICT`

- نفس truth chain
- مزيد من الرؤية والاعتماد والتسوية والتتبع
- لا duplicate posting engine

### anti-patterns ممنوعة

- ERP-lite جديد داخل `SIMPLE`
- duplicate workflow لأن صفحة جديدة أضيفت
- split truth between SIMPLE and STRICT

## 7. العقد غير المتصلة وoffline

### القاعدة

الـ offline جزء من النظام، لكنه لا يغيّر حقيقة الخادم.

### ما الذي يجب الحفاظ عليه؟

- idempotency
- atomic replay where required
- dead-letter visibility
- queue taxonomy الواضحة
- unified orchestrator للمزامنة

### مبدأ التصميم

offline ليس cache شكليًا؛ هو جزء من operational contract ويجب أن يبقى قابلًا للتشخيص والاختبار.

## 8. التقارير

### العقد المعتمد

- `GET /api/v1/advanced-report/` بدون `section_scope`:
  - direct usable payload
  - `summary + details`
- `section_scope`:
  - optimization explicit only

### قواعد واجهية

- helper محافظ للمسار المباشر
- helper sectional للمسار غير المتزامن
- لا reporting engine ثانٍ للمسارات المختلفة

## 9. الاختبارات والبوابات

### اختبارات أساسية

- backend targeted tests حسب الوحدة
- Vitest للواجهات
- Playwright للمسارات الحرجة

### البوابات الحاكمة

- `python scripts/verification/check_compliance_docs.py`
- `python backend/manage.py verify_static_v21`
- `python backend/manage.py verify_release_gate_v21`
- `python backend/manage.py verify_axis_complete_v21`

### لا تقل “اكتمل” إلا إذا

- الكود موجود
- doctrine محدثة
- skill محدثة عند الحاجة
- tests ذات الصلة مرّت
- latest canonical evidence بقيت `PASS/PASS`

## 10. الجاهزية والإصدار

### قواعد الجاهزية

- latest canonical evidence هي مصدر score authority
- evidence القديمة لا تتفوق على latest
- التوثيق العام لا يجب أن يناقض المرجع الحاكم

### ما الذي يعتبر فشلًا مرجعيًا؟

- code path موجود لكن غير موثق في doctrine أو skill
- docs public تدعي contract أقدم
- nav docs مكسورة أو تقود لمسارات غير موجودة

## 11. سياسة التمديد والتطوير

قبل إضافة feature أو surface جديد، اسأل:

1. هل هذا يفتح write path ثانيًا؟
2. هل هذا يكسر mode separation؟
3. هل هذا يكرر نفس posting logic؟
4. هل هذا ينقل policy من backend إلى frontend؟
5. هل هذا يخلق drift بين docs والكود؟

إذا كانت الإجابة نعم، فالتصميم يحتاج إعادة نظر.

## 12. HTML وWord

### السياسة المعتمدة

- HTML/MkDocs هو المرجع الحي
- Word نسخة مشتقة للتسليم أو الطباعة
- لا يتم تحرير Word مباشرة باعتباره source of truth

### لماذا؟

- أسهل في الصيانة
- أفضل للروابط الداخلية
- أفضل في code-adjacent docs
- يقلل drift بين النسخ

انظر أيضًا:

- `docs/word_export_policy_ar.md`

## 13. أين تقرأ بعد ذلك؟

- `docs/system_overview.md`
- `docs/API_REFERENCE.md`
- `docs/OFFLINE_OUTBOX.md`
- `docs/doctrine/DUAL_MODE_OPERATIONAL_CYCLES.md`
- `docs/doctrine/DAILY_EXECUTION_SMART_CARD.md`
- `docs/RUNBOOK.md`
