# دليل التشغيل والتحقق التنفيذي للمود البسيط على مزرعة سردود

> المرجع الحاكم:
> - `AGENTS.md`
> - `docs/prd/AGRIASSET_V21_MASTER_PRD_AR.md`
> - `docs/reference/REFERENCE_MANIFEST_V21.yaml`
> - `docs/reference/REFERENCE_PRECEDENCE_AND_OVERRIDE_V21.md`
>
> هذا الدليل هو المرجع التنفيذي الحالي لدورة `SIMPLE` على مزرعة `سردود`.
> أما [DUAL_MODE_MANUAL_CYCLE_GUIDE_AR_2026-03-27.md](C:/tools/workspace/AgriAsset_v44/docs/reports/DUAL_MODE_MANUAL_CYCLE_GUIDE_AR_2026-03-27.md)
> فيبقى مرجعًا تاريخيًا مختلطًا للمودين.

## 1. الهدف

هذا الدليل يثبت دورة تحقق كاملة للمود البسيط على مزرعة `سردود` مع:

- bootstrap وseed فعليين
- تحقق backend وfrontend
- walkthrough تشغيلي على الواجهة
- تشخيص findings
- توثيق الإصلاحات التي كانت لازمة لإنجاح الدورة

معيار النجاح هنا ليس فتح ERP مالي داخل `SIMPLE`، بل العكس:

- `SIMPLE` تبقى technical agricultural control surface
- المسارات المالية الصريحة تبقى محجوبة
- السلسلة الحاكمة تبقى:
  - `CropPlan -> DailyLog -> Activity -> Smart Card Stack -> Control -> Variance -> Ledger`

## 2. المتطلبات المسبقة

- PostgreSQL تعمل محليًا
- backend وfrontend يعملان
- لا يشترط Redis لإثبات دورة `SIMPLE` الأساسية
- المستخدم المرجعي:
  - `e2e_proof_user`
  - `E2EProof#2026`
- المزرعة المرجعية:
  - `مزرعة سردود`
  - `slug = sardood-farm`

## 3. أوامر التهيئة المرجعية

نفذت الأوامر التالية فعليًا في هذه الدفعة:

```powershell
python backend/manage.py prepare_e2e_auth_v21
python backend/manage.py seed_sardood_farm --clean --verbose
python backend/manage.py simulate_sardud_full_cycle
```

النتيجة الفعلية:

- `prepare_e2e_auth_v21` = `PASS`
  - `prepared_e2e_user=e2e_proof_user`
  - `prepared_proof_farm=sardood-farm`
  - `prepared_membership_scope=proof_farm_only`
- `seed_sardood_farm --clean --verbose` = `PASS`
  - أعاد بناء سردود كاملة
  - فعّل `show_daily_log_smart_card`
  - جهّز 4 خطط محاصيل وبيانات يومية وأشجار وحصاد ومخزون
- `simulate_sardud_full_cycle` = `PASS`
  - `farm_mode=SIMPLE`
  - `seasonal_cycle` نجح
  - `perennial_cycle` نجح
  - `variance_alert` تولد بنجاح

## 4. أوامر التحقق الخلفية

نفذت هذه الحزمة ومرّت:

```powershell
python backend/manage.py test smart_agri.core.tests.test_notifications_sse smart_agri.core.tests.test_prepare_e2e_auth_command smart_agri.core.tests.test_v21_e2e_cycle smart_agri.core.tests.test_v21_strict_route_leakage smart_agri.core.tests.test_route_breach_middleware smart_agri.core.tests.test_mode_policy_api --keepdb --noinput
pytest backend/smart_agri/core/tests/test_sardood_scenarios.py -q --maxfail=1 --reuse-db
```

النتيجة:

- Django targeted backend suite = `PASS`
- `test_sardood_scenarios` = `9 passed, 1 skipped`
- الـ skip الوحيد:
  - `No Cashbox for this farm to run PettyCashTest`
  - هذا ليس كسرًا لدورة `SIMPLE` الأساسية

## 5. أوامر التحقق الأمامية

نفذت الأوامر التالية ومرّت:

```powershell
npx --prefix frontend eslint frontend/src/hooks/useNotifications.js frontend/src/components/Nav.jsx frontend/src/hooks/useDailyLogForm.js frontend/src/components/daily-log/SmartCardStack.jsx frontend/src/pages/TreeCensus.jsx frontend/src/pages/settings/GovernanceTab.jsx frontend/tests/e2e/helpers/e2eAuth.js frontend/tests/e2e/helpers/e2eFixtures.js frontend/tests/e2e/sardud_simple_mode.spec.js frontend/tests/e2e/simple_mode_isolation.spec.js
npm --prefix frontend run build
npx --prefix frontend playwright test frontend/tests/e2e/sardud_simple_mode.spec.js --project=chromium --config=frontend/playwright.config.js --workers=1 --reporter=line
npx --prefix frontend playwright test frontend/tests/e2e/simple_mode_isolation.spec.js --project=chromium --config=frontend/playwright.config.js --workers=1 --reporter=line
```

النتيجة:

- `eslint` = `PASS`
- `frontend build` = `PASS`
- `sardud_simple_mode.spec.js` = `4 passed`
- `simple_mode_isolation.spec.js` = `2 passed`

## 6. مسار التشغيل التنفيذي على سردود

### 6.1 الدخول والسياق

- افتح:
  - `http://127.0.0.1:5173/login`
- سجّل بالمستخدم:
  - `e2e_proof_user`
- تأكد من اختيار مزرعة `سردود`

### 6.2 Dashboard

المتوقع:

- ظهور badge `وضع مبسط`
- عدم ظهور روابط authoring المالية الصريحة في التنقل
- ظهور health/alerts العربية دون fallback إنجليزي

### 6.3 Settings > Governance

الرابط:

- `/settings?tab=governance&farm=28`

المتوقع:

- ظهور `السياسة الفعالة`
- ظهور `الصحة التشغيلية`
- عدم سقوط الصفحة بالكامل إذا تعذر قسم جانبي
- بقاء الصفحة متاحة في `SIMPLE` و`STRICT` مع gating بالصلاحيات لا بالـ mode فقط

### 6.4 Daily Log الموسمي

المسار المرجعي الذي تم إثباته:

- farm: `سردود`
- crop: `طماطم`
- location: `حقل الخضروات - القطاع الجنوبي`
- task: `عملية موسمية E2E`

المتوقع:

- ظهور الخطة المرتبطة:
  - `خطة طماطم - سردود 2026`
- فتح خطوة الموارد
- قبول إدخال:
  - `labor_entry_mode = CASUAL_BATCH`
  - `casual_workers_count = 15`
  - `surra = 1.5`
- حفظ السجل بنجاح
- التحويل إلى `/daily-log-history`

### 6.5 Daily Log المعمّر

المسار المرجعي الذي تم إثباته:

- crop: `بن` أو `قات`
- task: `خدمة معمرة E2E`
- location: `حقل البن` أو `حقل القات`

المتوقع:

- ظهور الخطة المرتبطة بالمحصول المعمّر
- تحميل smart-card contract المعمّر
- ظهور مؤشرات ومعايير perennial execution
- في حال دعم الـ task صفوف الخدمة، تظهر صفوف variety/location-aware

مهم:

- إثبات write-side المعمّر الكامل تم تغطيته backend-side عبر:
  - `simulate_sardud_full_cycle`
- أما E2E فقد ثبتت surface/UI contract المعمّرة نفسها على الصفحة

### 6.6 Tree Census

الرابط:

- `/tree-census`

المتوقع:

- الصفحة متاحة في `SIMPLE`
- العنوان عربي
- الصفحة تعرض الجرد الشجري وتفاصيل الرصيد الجاري

### 6.7 Finance route blocking

المعيار الإلزامي:

- الدخول المباشر إلى:
  - `/finance/ledger`
- يجب ألا يفتح authoring مالي داخل `SIMPLE`

النتيجة المثبتة:

- الواجهة ترتد إلى `/dashboard`
- backend route-breach guard ما زال فعالًا
- هذا يعتبر `PASS` لا `FAIL`

## 7. الإصلاحات التي نُفذت خلال الدورة

### 7.1 إصلاح SSE مع JWT

المشكلة:

- `notifications/stream` كانت تعتمد جلسة Django فقط
- الواجهة تستخدم JWT
- النتيجة كانت redirect إلى `/accounts/login/?next=/api/v1/notifications/stream/`

الإصلاح:

- دعم `access_token` في SSE endpoint
- تمرير التوكن من `useNotifications`

الملفات:

- [notifications_sse.py](C:/tools/workspace/AgriAsset_v44/backend/smart_agri/core/api/notifications_sse.py)
- [test_notifications_sse.py](C:/tools/workspace/AgriAsset_v44/backend/smart_agri/core/tests/test_notifications_sse.py)
- [useNotifications.js](C:/tools/workspace/AgriAsset_v44/frontend/src/hooks/useNotifications.js)

### 7.2 إظهار Tree Census في SIMPLE

المشكلة:

- route كانت تعمل
- لكن عنصر التنقل كان مخفيًا على أساس `strictErpMode`

الإصلاح:

- جعل `Tree Census` ظاهرة في SIMPLE أيضًا

الملف:

- [Nav.jsx](C:/tools/workspace/AgriAsset_v44/frontend/src/components/Nav.jsx)

### 7.3 إصلاح debt واجهة Daily Log / Tree Census

الإصلاحات المنفذة:

- fallback عربي صحيح لدفعة العمالة اليومية
- تحسين formatter بطاقات smart cards لمنع عرض object خامة
- إزالة خلط لغوي ظاهر في عنوان `Tree Census`

الملفات:

- [useDailyLogForm.js](C:/tools/workspace/AgriAsset_v44/frontend/src/hooks/useDailyLogForm.js)
- [SmartCardStack.jsx](C:/tools/workspace/AgriAsset_v44/frontend/src/components/daily-log/SmartCardStack.jsx)
- [TreeCensus.jsx](C:/tools/workspace/AgriAsset_v44/frontend/src/pages/TreeCensus.jsx)

### 7.4 تحديث E2E إلى proof contract الحقيقي

المشكلة:

- الاختبارات كانت تعتمد `admin/ADMIN123`
- وكانت تختار أول مزرعة أو أول task بدل Sardood proof context

الإصلاح:

- اعتماد `e2e_proof_user`
- تفضيل `سردود` تلقائيًا في farm selection
- جعل assertions مرتبطة بالـ UI contract الحالي بدل assumptions قديمة

الملفات:

- [e2eAuth.js](C:/tools/workspace/AgriAsset_v44/frontend/tests/e2e/helpers/e2eAuth.js)
- [e2eFixtures.js](C:/tools/workspace/AgriAsset_v44/frontend/tests/e2e/helpers/e2eFixtures.js)
- [sardud_simple_mode.spec.js](C:/tools/workspace/AgriAsset_v44/frontend/tests/e2e/sardud_simple_mode.spec.js)
- [simple_mode_isolation.spec.js](C:/tools/workspace/AgriAsset_v44/frontend/tests/e2e/simple_mode_isolation.spec.js)

## 8. مصفوفة PASS / BLOCKED / FAIL

| البند | الحالة | الملاحظة |
|---|---|---|
| `prepare_e2e_auth_v21` | `PASS` | proof user + Sardood scope |
| `seed_sardood_farm --clean --verbose` | `PASS` | seed كاملة |
| `simulate_sardud_full_cycle` | `PASS` | seasonal + perennial + variance |
| backend targeted suites | `PASS` | mode + Sardood + route guards |
| Sardood pytest scenarios | `PASS` | `9 passed, 1 skipped` |
| Dashboard SIMPLE | `PASS` | badge + Arabic surface |
| Governance in SIMPLE | `PASS` | visible and working |
| Daily Log seasonal write-side | `PASS` | save confirmed |
| Daily Log perennial UI contract | `PASS` | plan + perennial smart contract |
| Tree Census in SIMPLE | `PASS` | page available |
| finance route block in SIMPLE | `PASS` | redirect + backend guard |
| full finance runtime inside SIMPLE | `BLOCKED BY DESIGN` | هذا حجب صحيح لا gap |

## 9. التحقق المرجعي بعد الإصلاح

نفذت:

```powershell
python scripts/verification/verify_release_hygiene.py
python backend/manage.py verify_release_gate_v21
python backend/manage.py verify_axis_complete_v21
```

النتيجة:

- `verify_release_hygiene.py` = `PASS`
- `verify_release_gate_v21` = `PASS`
- `verify_axis_complete_v21`
  - `axis_overall_status = PASS`
  - `overall_status = FAIL`

السبب:

- failure خارجي غير متعلق بدورة `SIMPLE` على سردود
- الفشل جاء من:
  - `axis_playwright_fuel`

الاستنتاج الصحيح:

- دورة `SIMPLE` على سردود نفسها `PASS`
- لكن claim gate شاملة على مستوى المستودع كله ما زالت متأثرة بـ blocker frontend آخر خارج scope هذه الدورة

## 10. معيار القبول النهائي لهذه الدورة

تعتبر دورة `SIMPLE` على سردود ناجحة عندما تجتمع الشروط التالية:

- أوامر Sardood المرجعية تمر
- المسارات اليومية/المعمرة التقنية تعمل
- `Settings > Governance` تبقى مرئية وعاملة في `SIMPLE`
- `Tree Census` متاحة في `SIMPLE`
- finance authoring لا تنفتح داخل `SIMPLE`
- أي محاولة direct breach تظل محكومة backend-side

## 11. ما لا يجب فعله

- لا توسّع `SIMPLE` إلى authoring مالي صريح
- لا تتجاوز `route breach guard`
- لا تنشئ posting engine مختلفًا للمود البسيط
- لا تكسر الربط:
  - `CropPlan -> DailyLog -> Activity -> Smart Card Stack -> Control -> Variance -> Ledger`

## 12. الخلاصة التنفيذية

الحالة الحالية بعد هذه الدفعة:

- مزرعة `سردود` أصبحت proof farm صالحة للمود البسيط
- دورة `SIMPLE` الأساسية مثبتة backend وfrontend
- أهم defects التي كانت تمنع الإثبات أُغلقت
- blocker المستودع المتبقي ليس في Sardood SIMPLE، بل في `axis_playwright_fuel` خارج نطاق هذا الدليل
