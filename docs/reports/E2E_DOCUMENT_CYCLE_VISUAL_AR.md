> [!IMPORTANT]
> Historical visual proof note only. This file is scoped evidence, not the live project score authority.
> Live authority: `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json`.

# تقرير الدورة المستندية البصرية - المود البسيط (2026-02-27)

## 1) بيئة التنفيذ
- نظام التشغيل: Windows
- قاعدة البيانات: PostgreSQL على `localhost:5432`
- الخلفية: Django على `http://127.0.0.1:8000`
- الواجهة: Vite على `http://127.0.0.1:5173`
- نمط تشغيل Playwright: تسلسلي `--workers=1`
- نطاق الجولة: **Simple Mode / مزرعة سردود**

## 2) الهدف
تنفيذ دورة تشغيل زراعية متكاملة من الواجهة في المود البسيط، مع أدلة تدقيقية كاملة وفق ضوابط `AGENTS.md`.

## 3) Baseline (قبل التنفيذ)
- `git status --short` => Clean
- `python backend/manage.py check` => PASS
- `python backend/manage.py migrate --plan` => PASS (`No planned migration operations`)
- `python backend/manage.py showmigrations` => جميع migrations مطبقة
- `python scripts/check_idempotency_actions.py` => PASS
- `python scripts/check_no_float_mutations.py` => PASS

## 4) تهيئة البيانات
### 4.1 المحاولة الأساسية
- `python backend/manage.py seed_full_system --clean --verbose` => **FAILED**
- السبب: `Task.MultipleObjectsReturned` أثناء `_seed_sardud_farm` بسبب تكرار بعض المهام.

### 4.2 المعالجة التشغيلية المعتمدة
- تم استخدام مسار بديل آمن وقابل للإعادة:
  - `python backend/manage.py seed_operational_catalog --clean-ops --season 2026` => PASS

### 4.3 تحقق بيانات سردود
- Farm: `مزرعة سردود` => موجود
- Crops: `مانجو`, `موز`, `قمح`, `ذرة صفراء`, `ذرة بيضاء` => موجودة
- Mango varieties: `قلب الثور`, `التيمور`, `السوداني`, `الزبدة` => موجودة
- Banana variety: `موز درجة اولى` => موجود
- `tasks_per_crop` => 5 لكل محصول
- `plans_sardud (season 2026)` => 5

## 5) فرض المود البسيط
- `strict_erp_mode` في DB => `False`
- `GET /api/v1/system-mode/` => `200`
- الاستجابة:
  - `"strict_erp_mode": false`
  - `"mode_label": "نظام مبسط (Shadow)"`

## 6) مصفوفة الاختبارات المنفذة
| Suite | Command | Result | Duration | ملاحظات |
|---|---|---|---:|---|
| Mode Access Unit | `npm --prefix frontend run test -- src/auth/__tests__/modeAccess.test.js --run` | PASS | ~1.97s | 3/3 |
| Simple Documentary Cycle | `npm --prefix frontend run test:e2e -- tests/e2e/simple_mode_document_cycle.spec.js --workers=1` | PASS | ~10.8s | login + daily-log + reports + strict route blocking |
| Daily Log Contracts | `npm --prefix frontend run test:e2e -- tests/e2e/daily-log.spec.js --workers=1` | PASS | ~15.7s | 3/3 (Surra + machine_hours context) |
| All Pages Navigation | `npm --prefix frontend run test:e2e -- tests/e2e/all_pages.spec.js --workers=1` | PASS | ~1.7m | 28/28 |
| Financial Workflow (تأكيدي) | `npm --prefix frontend run test:e2e -- tests/e2e/financial_workflow.spec.js --workers=1` | PASS | ~6.1s | 3/3 |

## 7) Post-run Compliance (بعد التنفيذ)
- `python backend/manage.py check` => PASS
- `python backend/manage.py migrate --plan` => PASS
- `python scripts/check_idempotency_actions.py` => PASS
- `python scripts/check_no_float_mutations.py` => PASS
- `python scripts/check_farm_scope_guards.py` => PASS
- `python scripts/check_fiscal_period_gates.py` => PASS

## 8) الأدلة (Artifacts)
- HTML report:
  - `frontend/.pw-results/playwright-report/index.html`
- traces/screenshots/videos:
  - `frontend/.pw-results/test-results/`

## 9) ملاحظات تشغيلية
- تنظيف artifacts القديمة عبر PowerShell كان محجوبًا بسياسة النظام في هذه الجولة، لكن Playwright أنشأ مخرجات الجولة الحالية ضمن `.pw-results` بنجاح.
- بلوكر `seed_full_system` موثق أعلاه ولم يمنع إغلاق نطاق الجولة لأن `seed_operational_catalog` حقق متطلبات بيانات الدورة المستهدفة.

## 10) القرار النهائي
- **Status: GO (ضمن نطاق Simple Mode + Sardud)**
- **Scope Result: PASS**
- **Compliance score لهذه الجولة التشغيلية: 100/100 (in-scope)**

## 11) خارج النطاق
- إصلاح دائم لخلل `seed_full_system` (تكرار Task) ليس ضمن هذه الجولة، ويوصى بفتح Issue مستقل له.
> [!IMPORTANT]
> Historical scoped E2E report only. Any score in this file is in-scope and dated.
> Live project authority: `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json`.
