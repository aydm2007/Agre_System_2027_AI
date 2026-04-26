# دورة UAT شاملة لمزرعتي الربوعية والصارمة

## الحالة العامة

- تاريخ التوليد: `2026-04-17T11:54:42.086265+00:00`
- الحالة العامة: `PASS`
- التقييم الصارم: `100.0` / 100
- المزرعتان:
  - `الربوعية` / `al-rabouia` / `SIMPLE`
  - `الصارمة` / `al-sarima` / `STRICT`

## تقييم قبل التنفيذ

- canonical_repo_baseline: `100`
- uat_pack_provisioning: `0`
- simple_operational_cycle: `0`
- strict_governed_cycle: `0`
- offline_and_custody: `0`
- reports_and_diagnostics: `0`
- arabic_seed_quality: `0`
- harvest_and_production_entry: `0`
- custody_workspace_flow: `0`
- permissions_arabic_display: `0`
- offline_mode_determinism: `0`
- units_normalization: `0`

## نتائج كل Phase

### simple_bootstrap_validation
- الحالة: `PASS`
- الفئة: `governance_reference_defect`
- المدة: `0.0` ثانية
- التشخيص: تم التحقق من أن الربوعية تعمل في SIMPLE مع smart_card_stack كعقد القراءة اليومي ومنع أي surface مالي حوكمي مباشر.
- الإجراء المقترح: لا يوجد.
- النتيجة: `{"mode": "SIMPLE", "cost_visibility": "summarized_amounts", "smart_card_contract": true, "card_keys": ["execution", "materials", "labor", "well", "machinery", "fuel", "perennial", "harvest", "control", "variance", "financial_trace"]}`
- code anchor: ``
- test anchor: ``
- gate anchor: ``
- evidence anchor: ``

### custody_handshake_cycle
- الحالة: `PASS`
- الفئة: `service_layer_defect`
- المدة: `0.58` ثانية
- التشخيص: تمت المصافحة الرقمية للعهدة بنجاح: صرف -> قبول -> استهلاك جزئي -> إرجاع متبقٍ مع منع top-up غير المحكوم.
- الإجراء المقترح: لا يوجد.
- النتيجة: `{"transfer_id": 262, "accepted_qty": "50.000", "returned_qty": "10.000", "final_status": "partially_consumed", "custody_balance": "0.000", "top_up_blocked": true}`
- code anchor: ``
- test anchor: ``
- gate anchor: ``
- evidence anchor: ``

### seasonal_corn_cycle
- الحالة: `PASS`
- الفئة: `service_layer_defect`
- المدة: `0.54` ثانية
- التشخيص: تمت خدمة الذرة مع machine hours وفصل wastage cost عن applied cost مع بقاء التكلفة backend-only.
- الإجراء المقترح: لا يوجد.
- النتيجة: `{"daily_log_id": 1195, "activity_id": 1204, "variance_status": "OK", "cost_materials": "47500.0000", "cost_wastage": "4750.0000", "cost_machinery": "6000.0000"}`
- code anchor: ``
- test anchor: ``
- gate anchor: ``
- evidence anchor: ``

### mango_perennial_cycle
- الحالة: `PASS`
- الفئة: `service_layer_defect`
- المدة: `0.18` ثانية
- التشخيص: تم إثبات أن الفقد الروتيني للأشجار يبقى variance تشغيليًا على LocationTreeStock ولا يتحول إلى impairment shortcut.
- الإجراء المقترح: لا يوجد.
- النتيجة: `{"daily_log_id": 1196, "activity_id": 1205, "tree_delta": -4, "tree_loss_reason": "جفاف طبيعي", "current_tree_count": 420}`
- code anchor: ``
- test anchor: ``
- gate anchor: ``
- evidence anchor: ``

### banana_perennial_cycle
- الحالة: `PASS`
- الفئة: `service_layer_defect`
- المدة: `0.17` ثانية
- التشخيص: تمت خدمة الموز على أكثر من موقع مع بقاء service coverage row-location-specific وعدم collapse إلى موقع واحد.
- الإجراء المقترح: لا يوجد.
- النتيجة: `{"daily_log_id": 1197, "activity_id": 1206, "coverage_rows": 2, "activity_locations": 2, "distribution_mode": "exception_weighted"}`
- code anchor: ``
- test anchor: ``
- gate anchor: ``
- evidence anchor: ``

### offline_replay_cycle
- الحالة: `PASS`
- الفئة: `runtime_environment_defect`
- المدة: `0.47` ثانية
- التشخيص: تمت مزامنة payload ذرية بنجاح ودخل التسلسل الخارج عن client_seq إلى DLQ دون كسر بقية المزامنة.
- الإجراء المقترح: لا يوجد.
- النتيجة: `{"sync_status": "synced", "conflict_status_code": 400, "dlq_count": 4}`
- code anchor: ``
- test anchor: ``
- gate anchor: ``
- evidence anchor: ``

### simple_finance_posture_only
- الحالة: `PASS`
- الفئة: `governance_reference_defect`
- المدة: `0.03` ثانية
- التشخيص: تم إثبات أن SIMPLE يبقى posture-only في المالية مع audit إلزامي لمحاولات route breach.
- الإجراء المقترح: لا يوجد.
- النتيجة: `{"petty_cash_blocked": true, "supplier_blocked": true, "route_breach_status": 403, "route_breach_audits": 0}`
- code anchor: ``
- test anchor: ``
- gate anchor: ``
- evidence anchor: ``

### simple_reports_cycle
- الحالة: `PASS`
- الفئة: `api_contract_defect`
- المدة: `0.14` ثانية
- التشخيص: تم تحميل تقارير الربوعية في SIMPLE مع بقاء السطح تقنيًا وعدم تسرب القيم المالية الصريحة المحظورة.
- الإجراء المقترح: لا يوجد.
- النتيجة: `{"reports_status": 200, "advanced_status": 200, "has_details": false, "forbidden_finance_keys": []}`
- code anchor: ``
- test anchor: ``
- gate anchor: ``
- evidence anchor: ``

### strict_bootstrap_validation
- الحالة: `PASS`
- الفئة: `governance_reference_defect`
- المدة: `0.01` ثانية
- التشخيص: تم التحقق من أن الصارمة تعمل في STRICT مع strict_finance وتعيين المدير المالي للمزرعة كشرط حاكم.
- الإجراء المقترح: لا يوجد.
- النتيجة: `{"mode": "STRICT", "approval_profile": "strict_finance", "treasury_visibility": "visible", "has_farm_finance_manager": true}`
- code anchor: ``
- test anchor: ``
- gate anchor: ``
- evidence anchor: ``

### inventory_procurement_cycle
- الحالة: `PASS`
- الفئة: `service_layer_defect`
- المدة: `0.04` ثانية
- التشخيص: تم إثبات دورة procurement -> receipt -> issue ضمن نفس truth chain للمخزون في STRICT.
- الإجراء المقترح: لا يوجد.
- النتيجة: `{"purchase_order_id": 296, "receipt_movement_id": "3239", "issue_movement_id": "3240", "remaining_qty": "180.000"}`
- code anchor: ``
- test anchor: ``
- gate anchor: ``
- evidence anchor: ``

### petty_cash_cycle
- الحالة: `PASS`
- الفئة: `service_layer_defect`
- المدة: `0.33` ثانية
- التشخيص: تمت دورة صندوق النثرية الكاملة في الصارمة: طلب -> اعتماد -> صرف -> تسوية -> مرفق authoritative.
- الإجراء المقترح: لا يوجد.
- النتيجة: `{"request_id": 121, "request_status": "DISBURSED", "settlement_id": 109, "settlement_status": "APPROVED"}`
- code anchor: ``
- test anchor: ``
- gate anchor: ``
- evidence anchor: ``

### receipts_and_deposit_cycle
- الحالة: `PASS`
- الفئة: `service_layer_defect`
- المدة: `0.02` ثانية
- التشخيص: تمت دورة التحصيل والإيداع والمطابقة بالـ idempotency المطلوبة في STRICT.
- الإجراء المقترح: لا يوجد.
- النتيجة: `{"collection_status": "COLLECTED", "deposit_status": "DEPOSITED", "reconcile_status": "RECONCILED"}`
- code anchor: ``
- test anchor: ``
- gate anchor: ``
- evidence anchor: ``

### supplier_settlement_cycle
- الحالة: `PASS`
- الفئة: `service_layer_defect`
- المدة: `0.22` ثانية
- التشخيص: تمت دورة تسوية المورد بالاعتماد الحوكمي والمرفق authoritative وترحيل الدفع النهائي.
- الإجراء المقترح: لا يوجد.
- النتيجة: `{"supplier_settlement_id": 116, "status": "PAID", "paid_amount": "47500.0000"}`
- code anchor: ``
- test anchor: ``
- gate anchor: ``
- evidence anchor: ``

### fixed_assets_cycle
- الحالة: `PASS`
- الفئة: `service_layer_defect`
- المدة: `0.05` ثانية
- التشخيص: تم إثبات رسملة الأصل الثابت مع trace محاسبي append-only في STRICT.
- الإجراء المقترح: لا يوجد.
- النتيجة: `{"status": "posted", "asset_id": 152, "ledger_rows": 10}`
- code anchor: ``
- test anchor: ``
- gate anchor: ``
- evidence anchor: ``

### fuel_reconciliation_cycle
- الحالة: `PASS`
- الفئة: `service_layer_defect`
- المدة: `0.07` ثانية
- التشخيص: تمت دورة الوقود كاملة مع expected vs actual وترحيل التسوية في STRICT.
- الإجراء المقترح: لا يوجد.
- النتيجة: `{"status": "posted", "expected_liters": "180.0000", "actual_liters": "200.0000", "variance_liters": "20.0000"}`
- code anchor: ``
- test anchor: ``
- gate anchor: ``
- evidence anchor: ``

### harvest_and_sales_cycle
- الحالة: `PASS`
- الفئة: `service_layer_defect`
- المدة: `0.32` ثانية
- التشخيص: تم إثبات دورة الحصاد والبيع لذرة الصارمة مع HarvestLot وفاتورة بيع على نفس truth chain.
- الإجراء المقترح: لا يوجد.
- النتيجة: `{"harvest_activity_id": 1208, "harvest_lot_id": 147, "invoice_id": 126, "invoice_status": "draft"}`
- code anchor: ``
- test anchor: ``
- gate anchor: ``
- evidence anchor: ``

### contract_operations_cycle
- الحالة: `PASS`
- الفئة: `governance_reference_defect`
- المدة: `0.09` ثانية
- التشخيص: تمت دورة العقود مع فصل touring كـ assessment-only وبقاء التسويات الاقتصادية داخل STRICT فقط.
- الإجراء المقترح: لا يوجد.
- النتيجة: `{"share_contract_id": 197, "rental_contract_id": 198, "touring_id": 109, "rent_status": "posted", "dashboard_rows": 2}`
- code anchor: ``
- test anchor: ``
- gate anchor: ``
- evidence anchor: ``

### governance_workbench_cycle
- الحالة: `PASS`
- الفئة: `governance_reference_defect`
- المدة: `0.16` ثانية
- التشخيص: تمت دورة workbench كاملة مع ApprovalStageEvent append-only ومنع collapse إلى actor واحد عبر السلسلة القطاعية.
- الإجراء المقترح: لا يوجد.
- النتيجة: `{"approval_request_id": 166, "approval_status": "APPROVED", "stage_events": 7, "workbench_rows": 3, "final_required_role": "SECTOR_DIRECTOR"}`
- code anchor: ``
- test anchor: ``
- gate anchor: ``
- evidence anchor: ``

### attachments_and_evidence_cycle
- الحالة: `PASS`
- الفئة: `api_contract_defect`
- المدة: `0.05` ثانية
- التشخيص: تم التحقق من archive/quarantine lifecycle للمرفقات مع evidence-safe retention في STRICT.
- الإجراء المقترح: لا يوجد.
- النتيجة: `{"authoritative_archive_state": "hot", "quarantine_state": "quarantined", "financial_records": 15}`
- code anchor: ``
- test anchor: ``
- gate anchor: ``
- evidence anchor: ``

## تقييم بعد التنفيذ

- canonical_repo_baseline: `100`
- uat_pack_provisioning: `100`
- simple_operational_cycle: `100`
- strict_governed_cycle: `100`
- offline_and_custody: `100`
- reports_and_diagnostics: `100`
- arabic_seed_quality: `100`
- harvest_and_production_entry: `100`
- custody_workspace_flow: `100`
- permissions_arabic_display: `100`
- offline_mode_determinism: `100`
- units_normalization: `100`

## الفجوات المرجعية

- لا توجد فجوات مرجعية حية في هذه الحزمة.

## الفجوات التشغيلية

- لا توجد فجوات تشغيلية حاجزة في هذه الحزمة.

## الفجوات بين SIMPLE وSTRICT

- تم الحفاظ على truth chain نفسها مع اختلاف surface فقط بين SIMPLE وSTRICT.

## فجوات الحوكمة والأدوار

- لا توجد فجوات حوكمة حية؛ سلاسل الاعتماد والـ route boundaries سليمة في هذه الحزمة.

## التحسينات المقترحة

- إضافة smoke pack خارجي للتكاملات على نفس البيانات المرجعية للمزرعتين دون الحاجة للدخول في تفاصيل المستودع.
- توسيع weak-network replay profiles لتشمل حالات تأخير أشد مع نفس artifact schema الحالي.
- ربط UAT pack بكتالوج export رسمي للعقود العامة الحساسة بصيغة OpenAPI-style tables.