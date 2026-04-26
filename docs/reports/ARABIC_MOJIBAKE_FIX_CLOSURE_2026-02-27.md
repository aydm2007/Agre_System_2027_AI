# تقرير إغلاق تشوّه النصوص العربية (Mojibake) — 2026-02-27

## الملخص
- الهدف: إصلاح تشوه النصوص العربية في الواجهات المتأثرة ومنع تكراره عبر بوابة CI مانعة.
- النطاق المنفذ:
  - `frontend/src/pages/CropPlans.jsx`
  - `frontend/src/pages/DailyLogHistory.jsx`
  - `frontend/src/components/ToastProvider.jsx`
  - `scripts/verification/check_mojibake_frontend.py`
  - `.github/workflows/ci.yml`
  - `.github/workflows/backend-postgres-tests.yml`
  - `scripts/verify_release_gate.sh`
  - `docs/PRODUCTION_RELEASE_GATE.md`

## قبل الإصلاح (Evidence)
- كانت تظهر أنماط تشوه نصية مثل: `Ø`, `Ù`, `Ã`, `ï¿½` داخل نصوص الواجهة.
- أثر المشكلة ظهر بصريًا في صفحات:
  - `/crop-plans`
  - `/daily-log-history`
- زر الإغلاق في `ToastProvider` كان مشوهًا.

## ما تم إصلاحه
1. إصلاح نصوص الصفحات المتأثرة إلى UTF-8 سليم.
2. إصلاح fallback message في `ToastProvider`.
3. إصلاح رمز زر الإغلاق في `ToastProvider` إلى رمز واضح.
4. إضافة فحص مانع جديد:
   - `python scripts/verification/check_mojibake_frontend.py`
5. ربط الفحص الجديد كـ blocking gate في CI وضمن release gate script.

## نتائج التحقق
### فحوص أساسية
- `python scripts/verification/check_mojibake_frontend.py` → PASS
- `python backend/manage.py check` → PASS
- `python backend/manage.py migrate --plan` → PASS
- `python scripts/check_idempotency_actions.py` → PASS
- `python scripts/check_no_float_mutations.py` → PASS

### فحوص الواجهة (Windows Sequential)
- `npm --prefix frontend run test -- src/auth/__tests__/modeAccess.test.js --run` → PASS
- `npm --prefix frontend run test:e2e -- tests/e2e/all_pages.spec.js --workers=1` → PASS
- `npm --prefix frontend run test:e2e -- tests/e2e/daily-log.spec.js --workers=1` → PASS
- `npm --prefix frontend run test:e2e -- tests/e2e/daily-log-history-governance.spec.js --workers=1` → PASS

ملاحظة تشغيلية: حدث فشل مؤقت عند تشغيل Suites متوازية؛ أُعيد التشغيل تسلسليًا وفق معيار Windows ونجحت النتائج.

## قرار الإغلاق
- الحالة: **Closed**
- النتيجة: النصوص العربية المتأثرة تم إصلاحها + تم تثبيت حارس CI مانع للتكرار.
- لا يوجد تغيير على API أو DB schema.
