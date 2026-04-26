# العقيدة المالية — Financial Doctrine
> [!IMPORTANT]
> المرجع الوحيد للقواعد المالية. المهارات تشير لهذا الملف ولا تكرر القواعد.

## 1. المحاسبة القائمة على الصناديق (Fund Accounting)
- إيرادات المزرعة **عهدة** (Custodial) — ليست ملكاً للمزرعة.
- حصيلة المبيعات تُرحّل لحساب القطاع الجاري (`ACCOUNT_SECTOR_PAYABLE`).
- المصروفات تُموّل فقط من طلبات تمويل معتمدة مرتبطة بـ `BudgetCode`.
- عند تأكيد البيع و`allow_revenue_recycling = False`: يُنشأ قيد تحويل تلقائي → لا يُحظر البيع.

## 2. الدفتر (Ledger) — Append-Only
- `FinancialLedger` لا يقبل `UPDATE` أو `DELETE` — فقط `INSERT`.
- التصحيح بعد `hard-close` = قيد عكسي في فترة مفتوحة.
- كل قيد يجب أن يحمل: `cost_center` + `crop_plan` (Analytical Purity).
- الخزينة (`TreasuryTransaction`) append-only أيضاً.

## 3. الفترات المالية (Fiscal Lifecycle)
```
open → soft-close → hard-close
```
- `open`: عمليات يومية للصراف.
- `soft-close`: تجميد للمراجعة — مدير المزرعة.
- `hard-close`: ختم نهائي — الإدارة العامة فقط.
- لا يُسمح بإقفال مباشر بضغطة واحدة.

### بوابة التوازن (Pre-Close Gate)
- قبل أي إقفال: `SUM(Debit) == SUM(Credit)` لكل مزرعة وفترة.
- التنفيذ: `LedgerBalancingService.validate_balances(farm_id, fiscal_period_id)`.
- عدم التوازن = `VarianceAlert` (CRITICAL) → يمنع الإقفال.

## 4. التسعير الآلي (Auto-Pricing)
- تأكيد البيع يتطلب تجاوز الحد الأدنى للسعر.
- المعادلة: `COGS (WAC) + 10% زكاة + 5% هامش أمان`.
- التسعير أقل = `ValidationError` — لا يوجد استثناء.

## 5. الزكاة (Sovereign Liabilities)
- الحصاد يُنشئ قيد زكاة تلقائياً.
- النسب حسب سياسة الري: `RAIN_10` (10%) | `WELL_5` (5%) | `MIXED_75` (7.5%).
- في وضع `enforce/full`: غياب السياسة = رفض العملية (لا fallback صامت).
- `Farm.zakat_rule` = fallback فقط في أوضاع `off/shadow`.

## 6. إقفال WIP الموسمي (Seasonal Settlement)
- نهاية الموسم: `DR 6000-COGS / CR 1400-WIP`.
- تكلفة الوحدة = `إجمالي WIP / الكمية المحصودة`.
- `CropPlan.status → SETTLED` بعد الإقفال.
- إقفال متكرر = يُعيد النتيجة المُخزّنة (idempotent).

## 7. الأصول البيولوجية (IAS 41)
- إعادة تقييم بالقيمة العادلة عند كل تقرير: `IAS41RevaluationService`.
- ربح: `DR 1600-BIO-ASSET / CR 5100-REVAL-GAIN`.
- خسارة: `DR 8100-REVAL-LOSS / CR 1600-BIO-ASSET`.
- إهلاك شهري للأشجار المنتجة: `DR 7000-DEP / CR 1600-BIO-ASSET`.

## 8. Decimal Purity
- **لا `float()` مطلقاً** في المسارات المالية والمخزنية.
- `Decimal(19, 4)` لكل الحقول المالية والكمية.
- التقريب بـ `quantize(Decimal('0.0001'))`.
