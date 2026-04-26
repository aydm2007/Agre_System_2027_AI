# Role / Permission / Mode Matrix (V21)

> هذه المصفوفة مقصود بها أن تكون **مرجع تنفيذ واختبار**، لا وصفًا أدبيًا فقط.

## 1) Local farm roles

| Role | SIMPLE | STRICT | SMALL | MEDIUM | LARGE | Notes |
|---|---|---|---|---|---|---|
| محاسب المزرعة | إدخال محلي + متابعة حالة | إدخال وتجهيز مستندات ودورات محلية | نعم | نعم | نعم | ليس صاحب الاعتماد النهائي |
| رئيس حسابات المزرعة | مراجعة محلية محدودة + جودة مستندية محلية | مراجعة محلية + soft close readiness + accounting pack review | قد يقوم بمهام إضافية وفق السياسة | نعم | نعم | في SMALL فقط قد يعمل acting FFM بسياسة واضحة؛ ليس بديلًا عن رئيس حسابات القطاع |
| المدير المالي للمزرعة | غالبًا مخفي أو محدود | اعتماد مالي محلي أعلى | اختياري/acting فقط إذا SMALL | إلزامي | إلزامي | لا يلغي السلسلة القطاعية |
| مدير المزرعة | تشغيل ورقابة | تشغيل ورقابة + اعتماد أعمالي عند الحاجة | نعم | نعم | نعم | ليس بديلًا عن السلسلة المالية |
| المهندس/المشرف | تشغيل يومي + DailyLog + Smart Card Stack | نفس الشيء | نعم | نعم | نعم | بدون authoring مالي |

## 2) Sector roles in STRICT

| Role | Visible in SIMPLE | Visible in STRICT | Mandatory | Key responsibilities |
|---|---|---|---|---|
| محاسب القطاع | مخفي غالبًا | نعم | نعم | first sector-side review |
| مراجع القطاع | مخفي غالبًا | نعم | نعم | second-line review / anomaly challenge |
| رئيس حسابات القطاع | مخفي غالبًا | نعم | نعم | governed accounting sign-off + reconciliation sign-off + close-readiness gate |
| المدير المالي لقطاع المزارع | مخفي غالبًا | نعم | نعم | policy and finance final lane |
| مدير القطاع | مخفي غالبًا | حسب السياسة | conditional | executive/business final approval |

## 3) Workflow expectations by mode

| Workflow | SIMPLE | STRICT | Required backend enforcement |
|---|---|---|---|
| Daily execution / DailyLog | تشغيل + رقابة + variance | تشغيل + رقابة + أثر مالي أعمق | same truth chain, no duplicate engine |
| Smart Card Stack | read-only | read-only | no direct ledger mutation |
| Finance / shadow journal root | قراءة فقط لقيود الظل اليومية | دفتر أستاذ كامل + treasury + governed trace | SIMPLE must stay outside governed `/finance/ledger/` authoring tree |
| Petty Cash | حالة وملخص | دورة كاملة | strict-only full authoring + sector final if policy says |
| Receipts | حالة ومخاطر | دورة كاملة مع أثر خزني | no finance route leakage in SIMPLE |
| Supplier Settlement | ملخص ذمم وحالة | مراجعة / اعتماد / سداد / تسوية | strict workflow with idempotency |
| Contracts | حالة وتوقعات + touring posture + expected share/rent | تسوية واستلام/دفع واعتماد + reconciliation posture | touring is assessment-only and not part of technical crop execution |
| Fixed Assets | سجل وصحة | رسملة وإهلاك وتحكم | governed posting only |
| Tree Ledger / Perennial Assets | رؤية جردية بسيطة + تعديلات جماعية | سجل إهلاك كامل وحركات رسملة | backend variance generation for EXCLUDED status |
| Fuel | انحراف ومخاطر | تسوية مفصلة | governed reconciliation |
| Attachments | خفيفة ومحدودة | مصنفة ومؤرشفة ومحوكمة | classification and retention policy |

## 3.1) Workflow gate ownership

| Workflow | Farm accountant | Farm chief accountant | Farm finance manager | Sector chief accountant | Sector finance director |
|---|---|---|---|---|---|
| Petty Cash | prepare request and settlement pack | local accounting review and pack quality | local strict gate where configured | reconciliation sign-off when sector path is required | sector-final under `strict_finance` or exception thresholds |
| Supplier Settlement | payable preparation and evidence completion | local review and accounting-pack completeness | local payment-readiness gate | accounting sign-off and reconciliation gate | sector-final for governed posting thresholds and exceptions |
| Contract payment posting | contract pack preparation only | local accounting review only | local gate where policy allows | accounting sign-off on settlement readiness | final posting authority where policy requires sector-final |
| Fixed Assets | register preparation and evidence intake | local register quality and capitalization-pack review | local strict gate for governed action requests | capitalization/disposal reconciliation sign-off | sector-final for governed capitalization/disposal actions under policy |
| Fuel Reconciliation | anomaly preparation and source evidence completion | local reconciliation-pack review | local strict gate for governed reconciliation requests | reconciliation sign-off and sector close-readiness gate | sector-final for governed posting actions under `strict_finance` |
| Fiscal close | local close pack preparation | soft-close readiness and accounting-pack quality | farm-level close gate for `MEDIUM/LARGE` | sector close-readiness sign-off | hard-close authority |

Interpretation rules:
- `رئيس حسابات المزرعة` is a local accounting-review and soft-close-readiness role only.
- `رئيس حسابات القطاع` is the accounting sign-off and reconciliation gate at sector level.
- `المدير المالي للمزرعة` does not replace the sector chain.
- `SMALL` farms may use acting local finance authority only when explicit policy and compensating controls allow it.

## 4) Enforcement requirements
- لا يكفي إخفاء القوائم أو الروابط في `SIMPLE`.
- يجب أن تمنع API وservice layer أي authoring مالي كامل خارج `STRICT`.
- `MEDIUM/LARGE` يجب أن تفشل صلاحياتيًا إذا غاب `المدير المالي للمزرعة`.
- `SMALL` لا يعمل بصلاحية مدمجة إلا إذا تحققت:
  - farm tier = SMALL
  - `single_finance_officer_allowed=true`
  - thresholds enforced
  - sector final close mandatory

## 5) Tests that should exist
- mode access tests for route registration and navigation visibility
- permission tests for final posting actions
- approval chain tests preventing single-role collapse
- farm-size policy tests
- reopening/override authorization tests

## 5.1) Import / Export Platform

| Capability | SIMPLE | STRICT | Notes |
|---|---|---|---|
| تنزيل تقارير `XLSX` | نعم حسب نطاق المزرعة والصلاحية | نعم | الصيغة الأساسية الموجهة للمستخدم |
| تنزيل تقارير `JSON` | نعم حسب نفس نطاق التقرير | نعم | صيغة تقنية اختيارية، لا تتجاوز visibility الحاكم |
| تنزيل قالب `inventory_count_sheet` | نعم | نعم | تشغيلي وآمن |
| تنزيل قالب `inventory_operational_adjustment` | نعم | نعم | تشغيلي وآمن |
| رفع قالب `inventory_count_sheet` | نعم | نعم | لا كتابة مباشرة قبل validation/apply |
| رفع قالب `inventory_operational_adjustment` | نعم | نعم | لا يفتح ledger authoring |
| تنزيل قالب `inventory_opening_balance` | لا | نعم | STRICT-only |
| تنزيل قالب `inventory_item_master` | لا | نعم | STRICT-only |
| رفع/تطبيق `inventory_opening_balance` | لا | نعم | governed inventory master/opening path |
| رفع/تطبيق `inventory_item_master` | لا | نعم | governed master-data path |
| تنزيل قالب `planning_master_schedule` | نعم | نعم | تشغيلي بحسب المود |
| تنزيل قالب `planning_crop_plan_structure` | نعم | نعم | يتطلب `crop_plan_id` صالحًا |
| رفع/تطبيق `planning_master_schedule` | نعم | نعم | لا يفتح authoring مالي مباشر |
| رفع/تطبيق `planning_crop_plan_structure` | نعم | نعم | service-layer only + preview/apply |
| تنزيل قالب `planning_crop_plan_budget` | لا | نعم | STRICT-only |
| رفع/تطبيق `planning_crop_plan_budget` | لا | نعم | تخطيط/ميزانية مرتبطة بالخطة فقط، مع gate backend |

قواعد التفسير:
- `XLSX` هو الصيغة الأساسية business-facing في هذه الموجة.
- `JSON` اختياري للتكامل والتحليل فقط.
- لا `CSV` في الواجهات user-facing الخاصة بهذه المنصة.
- `SIMPLE` يسمح فقط باستيرادات تشغيلية posture-safe، ولا يسمح بقوالب master/opening balance.
- `SIMPLE` يسمح كذلك فقط باستيرادي التخطيط التشغيليين: `planning_master_schedule` و`planning_crop_plan_structure`.
- `planning_crop_plan_budget` يبقى `STRICT-only` حتى لو حاولت الواجهة إخفاء أو إظهار الزر بشكل خاطئ؛ القرار الحاكم في backend.
- القرار النهائي للصلاحية في backend، وليس في إخفاء الزر فقط.

## 5.2) Report Registry Scope by Mode

| Report group / export type family | SIMPLE | STRICT | Notes |
|---|---|---|---|
| `execution` | نعم | نعم | `daily_execution_summary`, `daily_execution_detail` |
| `variance` | نعم | نعم | `plan_actual_variance` مع posture-safe payload في SIMPLE |
| `perennial` | نعم | نعم | `perennial_tree_balance` |
| `readiness` | نعم | نعم | `operational_readiness` |
| `inventory` | نعم | نعم | operational inventory reports and expiry posture |
| `fuel` | summarized posture only | full posture/detail by policy | no finance authoring in SIMPLE |
| `fixed_assets` | tracking / posture only | full governed detail | same backend truth, no duplicate engine |
| `contracts` | posture only | governed detail | touring remains assessment-only |
| `finance` (`supplier`, `petty_cash`, `receipts`) | summarized posture only | full governed detail | JSON download remains role-gated |
| `governance` | no ordinary field visibility | sector / strict lanes only | `governance_work_queue` is not a SIMPLE surface |

Interpretation:
- `Reports Hub` owns shared analytical and operational catalogs.
- module-local dashboards may expose governed-heavy exports, but backend policy remains authoritative.
- `role_scope` on the export definition controls who may see and run a report even inside `STRICT`.

## 6) Transitional Compatibility Debt
- `show_finance_in_simple`, `show_stock_in_simple`, and `show_employees_in_simple` are `compatibility-only` and `display-only` flags.
- These flags are `not authoring authority` for backend mutation, governed `/finance/ledger/` route registration, governed stock writes, or payroll authoring in `SIMPLE`.
- Read-only shadow-journal visibility in `/finance` for `SIMPLE` is a governed read surface over the same ledger truth, not a reopening of finance authoring authority.
- Canonical enforcement remains in `backend/smart_agri/core/permissions.py` and `backend/smart_agri/core/middleware/route_breach_middleware.py`.
