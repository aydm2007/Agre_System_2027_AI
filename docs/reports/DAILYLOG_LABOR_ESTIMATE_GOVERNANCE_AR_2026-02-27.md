# تقرير تدقيقي: توحيد Labor Estimate وواجهة Surra في Daily Log (2026-02-27)

## 1) الملخص التنفيذي
- الهدف: إغلاق فجوة UX/حوكمة العمالة اليومية مع الحفاظ على العقيدة المالية (`Surra` كوحدة محاسبية).
- النتيجة: تم اعتماد endpoint قراءة فقط للتقدير الفوري + تحديث واجهة Daily Log + تغطية اختبارات backend/frontend/e2e.
- الحالة: **PASS** ضمن النطاق المستهدف.

## 2) Before / After
### قبل
- التسمية التشغيلية للعمالة اليومية غير مستقرة (سرة/صرة) وتسبب التباساً.
- لا يوجد ملخص مرئي فوري للساعات المكافئة/تكلفة العمالة التقديرية.
- لا يوجد عقد API رسمي read-only للتقدير اللحظي.

### بعد
- التسمية القياسية: `عدد الفترات (Surra)`.
- تم إضافة helper واضح: `الفترة = 8 ساعات` كمرجع تشغيلي فقط.
- تم إضافة لوحة تقدير مرئية بعقود testid ثابتة:
  - `labor-estimate-panel`
  - `equivalent-hours-per-worker`
  - `equivalent-hours-total`
  - `estimated-labor-cost`
- تم إضافة endpoint جديد:
  - `POST /api/v1/labor-estimates/preview/` (read-only, farm-scoped, Decimal-safe).

## 3) العقد الجديد (Backend + Frontend + Governance)
### Backend Contract
- endpoint: `POST /api/v1/labor-estimates/preview/`
- input: `farm_id`, `labor_entry_mode`, `surrah_count`, `period_hours?`, `workers_count?`, `employee_ids?`
- output: `period_hours`, `surrah_count`, `equivalent_hours_per_worker`, `equivalent_hours_total`, `estimated_labor_cost`, `currency`, `rate_basis`
- controls: farm-scope mandatory, no side-effects, Decimal string formatting.

### Frontend Contract
- Daily Log Resources يعرض التقدير في نمطي `REGISTERED` و`CASUAL_BATCH` عند اكتمال المدخلات.
- `machine_hours` بقيت ضمن بطاقة الآلات فقط.

### Governance Contract
- إلزام تدريجي (scope-based mandatory):
  - عند تغييرات Daily Log/Labor UX تصبح اختبارات labor-estimate backend + daily-log e2e إلزامية.
  - خارج النطاق ليست blocker عالمي.

## 4) Results Matrix (Findings-first)
### Findings Critical
- لا يوجد.

### Findings High
- لا يوجد.

### Findings Medium
- فشل عابر في E2E بسبب انقطاع backend أثناء تشغيل متسلسل؛ أُعيد التشغيل ونجح.
- فشل assertion في E2E بسبب شرط نصي غير دقيق (`0.00` ضمن رقم أكبر)؛ تم تصحيح assertion ونجح.

## 5) أوامر التحقق ونتائجها
| Command | Result |
|---|---|
| `python backend/manage.py check` | PASS |
| `python backend/manage.py migrate --plan` | PASS (No planned operations) |
| `python scripts/check_idempotency_actions.py` | PASS |
| `python scripts/check_no_float_mutations.py` | PASS |
| `python scripts/check_farm_scope_guards.py` | PASS |
| `python scripts/check_fiscal_period_gates.py` | PASS |
| `python backend/manage.py test smart_agri.core.tests.test_labor_estimation_api --keepdb --noinput` | PASS (6 tests) |
| `npm --prefix frontend run test -- src/auth/__tests__/modeAccess.test.js --run` | PASS |
| `npm --prefix frontend run test -- src/components/daily-log/__tests__/DailyLogResources.test.jsx --run` | PASS |
| `npm --prefix frontend run test:e2e -- tests/e2e/daily-log.spec.js --workers=1` | PASS |
| `npm --prefix frontend run test:e2e -- tests/e2e/daily-log-seasonal-perennial.spec.js --workers=1` | PASS |
| `npm --prefix frontend run test:e2e -- tests/e2e/simple_mode_document_cycle.spec.js --workers=1` | PASS |

## 6) تقييم صارم (Score)
- قبل التحديث: **84/100**
- بعد التحديث: **96/100**

### مبررات الدرجة الحالية (الـ 4 المتبقية)
1. لم يتم بعد إدخال gate مركزي آلي في CI يفرض اختبار labor-estimate عند أي تعديل بملفات Daily Log (حاليًا موثق لكنه غير مؤتمت بالكامل).
2. ما يزال الأداء تحت ضغط الشبكة الضعيفة يحتاج جولة تحميل/latency مخصصة لهذا endpoint الجديد ضمن E2E سيناريوهات واسعة.

## 7) القرار النهائي
- **GO (ضمن النطاق)**: التحديثات متوافقة مع AGENTS doctrine، بدون كسر محاور الامتثال الأساسية.
- **متابعة مستحسنة**: إضافة CI rule scope-aware لتفعيل إلزام اختبارات labor-estimate تلقائيًا عند تعديل ملفات Daily Log.
