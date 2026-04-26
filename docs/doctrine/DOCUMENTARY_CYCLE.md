# الدورة المستندية الشاملة — Documentary Cycle

هذا المستند يصف التدفق التنفيذي والمالي المرجعي من التخطيط إلى الإقفال، مع تثبيت
`Smart Card Stack` كسطح read-side داخل التنفيذ اليومي.

## 1. الخطة الزراعية والميزانية
- الدور: مدير المزرعة / المهندس الزراعي
- الإجراء: إنشاء `CropPlan` للموسم والمحصول والموقع
- البيانات: `expected_yield`, `budget_materials`, `budget_labor`, `budget_machinery`
- التحقق: farm scope + `Decimal` only

## 2. المشتريات والاستلام
- الدور: مدير المزرعة → أمين المخزن
- الإجراء: طلب شراء → استلام → إدخال مخزني
- التدفق: `PurchaseOrder -> StockMovement`
- المالية: `DR Inventory / CR Payable or Cash`
- التحقق: `X-Idempotency-Key` + `AuditLog` + policy approvals

## 3. التنفيذ اليومي
- الدور: المشرف الميداني / أمين المخزن
- الإجراء: صرف مواد + تسجيل `DailyLog` + إنشاء/تعديل `Activity`
- التدفق: `StockMovement (issue) -> Activity`
- العمالة: Surra-based only
- التحقق: non-negative inventory + BOM comparison + diesel/fuel checks when relevant

## 4. Smart Card Stack داخل DailyLog
- المسار المرجعي:
  - `CropPlan -> DailyLog -> Activity -> Smart Card Stack -> Control -> Variance -> Ledger`
- `Activity` تبقى سجلًا تشغيليًا واحدًا مرتبطًا بـ `Task` واحدة.
- `Smart Card Stack` سطح read-side فقط؛ لا ينشئ قيودًا ولا يعتمدها.
- الـ stack يُشتق من:
  - `Activity.task_contract_snapshot`
  - fallback إلى `Task.task_contract` للأنشطة القديمة فقط
- البطاقات القياسية:
  - `execution`
  - `materials`
  - `labor`
  - `well`
  - `machinery`
  - `fuel`
  - `perennial`
  - `harvest`
  - `control`
  - `variance`
  - `financial_trace`
- `SIMPLE` يعرض فقط البطاقات المسموح بها من `simple_preview`.
- `STRICT` يعرض نفس الحقيقة التشغيلية مع `strict_preview` وتفصيل governed أعمق.
- الحقول القديمة مثل `task_focus` و`plan_metrics` تبقى طبقة توافق مؤقتة فقط.

## 5. الحصاد والزكاة
- الدور: المهندس الزراعي / مدير المزرعة
- الإجراء: `HarvestActivity`
- التدفق: `StockMovement (receipt) + DR Inventory / CR WIP`
- الزكاة: حسب سياسة الري
- التحقق: idempotency + fiscal gate + audit + Zakat quarantine where required

## 6. المبيعات والتحصيل
- الدور: أمين الصندوق / محاسب المبيعات
- الإجراء: بيع المحصول → تحصيل نقدي أو عهدة
- التدفق: `SalesInvoice -> TreasuryTransaction`
- التحقق: minimum price rules + treasury trace + settlement posture

## 7. الإقفال المالي
- التسلسل: `open -> soft-close -> hard-close`
- الأدوار: صراف → مدير المزرعة → رئيس الحسابات / السلسلة القطاعية
- الشرط: `SUM(DR) == SUM(CR)`
- التصحيح: reverse + repost فقط، لا overwrite صامت

## 8. العهد النقدية وتسوياتها
- `PettyCashRequest -> approval -> disbursement -> PettyCashSettlement`
- التحقق: idempotency + farm scope + liability trace

## 9. تسويات الموردين
- `PurchaseOrder -> SupplierSettlement -> approval -> payment`
- التحقق: farm scope + finance authority + outstanding balance + traceability

## 10. المصروفات الفعلية والتخصيص
- `ActualExpense -> fiscal validation -> allocation`
- التحقق: budget code + replenishment reference + fiscal gate

## 11. الأصول الثابتة والوقود
- الأصول الثابتة:
  - register -> depreciation posture -> capitalization posture by policy
- الوقود:
  - machine card -> expected vs actual -> anomaly/reconciliation posture
- التحقق:
  - policy snapshot موحد بين `SIMPLE` و`STRICT`
  - لا تكرار لمنطق المودات أو لمحرك الترحيل

## قواعد حاكمة
- `Smart Card Stack` ليس write-path.
- costing يبقى backend-only.
- لا multi-task activity.
- لا duplicate posting engine.
- `SIMPLE/STRICT` يختلفان في surface فقط لا في business truth.
