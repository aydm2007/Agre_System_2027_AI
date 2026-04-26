# دورة UAT شاملة لمزرعتي الربوعية والصارمة

## الحالة العامة

- تاريخ التوليد: `2026-04-09T11:10:03.511332+00:00`
- الحالة العامة: `FAIL`
- التقييم الصارم: `84.21` / 100
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
- الحالة: `FAIL`
- الفئة: `service_layer_defect`
- المدة: `0.06` ثانية
- التشخيص: ['']
- الإجراء المقترح: إذا فشل هذا الطور فافحص issue/accept/return lifecycle وcustody balance refresh وقيود top-up.
- النتيجة: `{}`
- code anchor: `backend/smart_agri/core/services/custody_transfer_service.py ; backend/smart_agri/core/services/activity_item_service.py`
- test anchor: `backend/smart_agri/core/tests/test_custody_transfer_service.py ; backend/smart_agri/core/tests/test_activity_custody_items.py`
- gate anchor: `python backend/manage.py verify_axis_complete_v21`
- evidence anchor: `docs\evidence\uat\rabouia-sarima\run-20260409-0410\summary.json`

### seasonal_corn_cycle
- الحالة: `FAIL`
- الفئة: `service_layer_defect`
- المدة: `0.07` ثانية
- التشخيص: ['']
- الإجراء المقترح: إذا فشل هذا الطور فافحص applied_qty/waste_qty وmachine_hours وsingle-crop costing.
- النتيجة: `{}`
- code anchor: `backend/smart_agri/finance/services/costing_service.py ; backend/smart_agri/core/api/serializers/activity.py`
- test anchor: `backend/smart_agri/core/tests/test_activity_custody_items.py ; backend/smart_agri/core/tests/test_schedule_variance.py`
- gate anchor: `python backend/manage.py verify_axis_complete_v21`
- evidence anchor: `docs\evidence\uat\rabouia-sarima\run-20260409-0410\summary.json`

### mango_perennial_cycle
- الحالة: `PASS`
- الفئة: `service_layer_defect`
- المدة: `0.21` ثانية
- التشخيص: تم إثبات أن الفقد الروتيني للأشجار يبقى variance تشغيليًا على LocationTreeStock ولا يتحول إلى impairment shortcut.
- الإجراء المقترح: لا يوجد.
- النتيجة: `{"daily_log_id": 452, "activity_id": 515, "tree_delta": -4, "tree_loss_reason": "جفاف طبيعي", "current_tree_count": 420}`
- code anchor: ``
- test anchor: ``
- gate anchor: ``
- evidence anchor: ``

### banana_perennial_cycle
- الحالة: `PASS`
- الفئة: `service_layer_defect`
- المدة: `0.15` ثانية
- التشخيص: تمت خدمة الموز على أكثر من موقع مع بقاء service coverage row-location-specific وعدم collapse إلى موقع واحد.
- الإجراء المقترح: لا يوجد.
- النتيجة: `{"daily_log_id": 453, "activity_id": 516, "coverage_rows": 2, "activity_locations": 2, "distribution_mode": "exception_weighted"}`
- code anchor: ``
- test anchor: ``
- gate anchor: ``
- evidence anchor: ``

### offline_replay_cycle
- الحالة: `FAIL`
- الفئة: `runtime_environment_defect`
- المدة: `0.09` ثانية
- التشخيص: ['']
- الإجراء المقترح: إذا فشل هذا الطور فافحص idempotency key وclient_seq وDLQ routing.
- النتيجة: `{}`
- code anchor: `backend/smart_agri/core/api/viewsets/offline_replay.py ; frontend/src/offline/SyncManager.js`
- test anchor: `backend/smart_agri/core/tests/test_offline_daily_log_replay.py`
- gate anchor: `python backend/manage.py verify_axis_complete_v21`
- evidence anchor: `docs\evidence\uat\rabouia-sarima\run-20260409-0410\summary.json`

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
- المدة: `0.12` ثانية
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
- المدة: `0.0` ثانية
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
- المدة: `0.03` ثانية
- التشخيص: تم إثبات دورة procurement -> receipt -> issue ضمن نفس truth chain للمخزون في STRICT.
- الإجراء المقترح: لا يوجد.
- النتيجة: `{"purchase_order_id": 42, "receipt_movement_id": "475", "issue_movement_id": "476", "remaining_qty": "180.000"}`
- code anchor: ``
- test anchor: ``
- gate anchor: ``
- evidence anchor: ``

### petty_cash_cycle
- الحالة: `PASS`
- الفئة: `service_layer_defect`
- المدة: `0.35` ثانية
- التشخيص: تمت دورة صندوق النثرية الكاملة في الصارمة: طلب -> اعتماد -> صرف -> تسوية -> مرفق authoritative.
- الإجراء المقترح: لا يوجد.
- النتيجة: `{"request_id": 37, "request_status": "DISBURSED", "settlement_id": 25, "settlement_status": "APPROVED"}`
- code anchor: ``
- test anchor: ``
- gate anchor: ``
- evidence anchor: ``

### receipts_and_deposit_cycle
- الحالة: `PASS`
- الفئة: `service_layer_defect`
- المدة: `0.03` ثانية
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
- المدة: `0.18` ثانية
- التشخيص: تمت دورة تسوية المورد بالاعتماد الحوكمي والمرفق authoritative وترحيل الدفع النهائي.
- الإجراء المقترح: لا يوجد.
- النتيجة: `{"supplier_settlement_id": 32, "status": "PAID", "paid_amount": "47500.0000"}`
- code anchor: ``
- test anchor: ``
- gate anchor: ``
- evidence anchor: ``

### fixed_assets_cycle
- الحالة: `PASS`
- الفئة: `service_layer_defect`
- المدة: `0.04` ثانية
- التشخيص: تم إثبات رسملة الأصل الثابت مع trace محاسبي append-only في STRICT.
- الإجراء المقترح: لا يوجد.
- النتيجة: `{"status": "posted", "asset_id": 32, "ledger_rows": 10}`
- code anchor: ``
- test anchor: ``
- gate anchor: ``
- evidence anchor: ``

### fuel_reconciliation_cycle
- الحالة: `PASS`
- الفئة: `service_layer_defect`
- المدة: `0.16` ثانية
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
- المدة: `0.28` ثانية
- التشخيص: تم إثبات دورة الحصاد والبيع لذرة الصارمة مع HarvestLot وفاتورة بيع على نفس truth chain.
- الإجراء المقترح: لا يوجد.
- النتيجة: `{"harvest_activity_id": 517, "harvest_lot_id": 45, "invoice_id": 32, "invoice_status": "draft"}`
- code anchor: ``
- test anchor: ``
- gate anchor: ``
- evidence anchor: ``

### contract_operations_cycle
- الحالة: `PASS`
- الفئة: `governance_reference_defect`
- المدة: `0.07` ثانية
- التشخيص: تمت دورة العقود مع فصل touring كـ assessment-only وبقاء التسويات الاقتصادية داخل STRICT فقط.
- الإجراء المقترح: لا يوجد.
- النتيجة: `{"share_contract_id": 29, "rental_contract_id": 30, "touring_id": 25, "rent_status": "posted", "dashboard_rows": 2}`
- code anchor: ``
- test anchor: ``
- gate anchor: ``
- evidence anchor: ``

### governance_workbench_cycle
- الحالة: `PASS`
- الفئة: `governance_reference_defect`
- المدة: `0.29` ثانية
- التشخيص: تمت دورة workbench كاملة مع ApprovalStageEvent append-only ومنع collapse إلى actor واحد عبر السلسلة القطاعية.
- الإجراء المقترح: لا يوجد.
- النتيجة: `{"approval_request_id": 47, "approval_status": "APPROVED", "stage_events": 7, "workbench_rows": 3, "final_required_role": "SECTOR_DIRECTOR"}`
- code anchor: ``
- test anchor: ``
- gate anchor: ``
- evidence anchor: ``

### attachments_and_evidence_cycle
- الحالة: `PASS`
- الفئة: `api_contract_defect`
- المدة: `0.04` ثانية
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
- simple_operational_cycle: `0`
- strict_governed_cycle: `100`
- offline_and_custody: `0`
- reports_and_diagnostics: `100`
- arabic_seed_quality: `0`

## الفجوات المرجعية

- لا توجد فجوات مرجعية حية في هذه الحزمة.

## الفجوات التشغيلية

- custody_handshake_cycle
- seasonal_corn_cycle
- offline_replay_cycle

## الفجوات بين SIMPLE وSTRICT

- تم الحفاظ على truth chain نفسها مع اختلاف surface فقط بين SIMPLE وSTRICT.

## فجوات الحوكمة والأدوار

- لا توجد فجوات حوكمة حية؛ سلاسل الاعتماد والـ route boundaries سليمة في هذه الحزمة.

## التحسينات المقترحة

- إضافة smoke pack خارجي للتكاملات على نفس البيانات المرجعية للمزرعتين دون الحاجة للدخول في تفاصيل المستودع.
- توسيع weak-network replay profiles لتشمل حالات تأخير أشد مع نفس artifact schema الحالي.
- ربط UAT pack بكتالوج export رسمي للعقود العامة الحساسة بصيغة OpenAPI-style tables.