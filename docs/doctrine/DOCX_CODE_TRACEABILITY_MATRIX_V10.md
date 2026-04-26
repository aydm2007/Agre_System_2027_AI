# DOCX -> Code Traceability Matrix (V10)

This matrix keeps documentary-cycle assets aligned with implemented code paths, service ownership, and current status.
This is the active documentary traceability reference. Older V3-V9 matrices are historical snapshots only.

| Docx file | Decoded title | Workflow | API/UI surface | Service owner | Status |
|---|---|---|---|---|---|
| `#U0627#U0644#U0627#U0635#U0648#U0631 #U0627#U0644#U062b#U0627#U0628#U062a#U0629.docx` | الاصور الثابتة.docx | Fixed Assets | `core/views/fixed_assets_dashboard.py` | `core/services/fixed_asset_workflow_service.py` | implemented with governed capitalization/disposal evidence |
| `#U0627#U0644#U0627#U064a#U062c#U0627#U0631#U0627#U062a.docx` | الايجارات.docx | Contract Operations / Rentals | `core/services/contract_operations_service.py` | `core/services/contract_operations_service.py` | implemented |
| `#U0627#U0644#U0634#U0631#U0627#U0643 #U0648#U0627#U0644#U0637#U0648#U0627#U0641.docx` | الشراك والطواف.docx | Contract Operations / Sharecropping & Touring | `core/services/contract_operations_service.py` | `core/services/contract_operations_service.py` | implemented |
| `#U0627#U0644#U0645#U0642#U0628#U0648#U0636#U0627#U062a.docx` | المقبوضات.docx | Receipts and Deposit | `finance/api_treasury.py` | `finance/services/treasury_service.py` | implemented |
| `#U0627#U0644#U0646#U0641#U0642#U0627#U062a #U0627#U0644#U062a#U0634#U063a#U064a#U0644#U064a#U0629- #U0634#U0631#U0627#U0621 #U0627#U062d#U062a#U064a#U0627#U062c#U0627#U062a.docx` | النفقات التشغيلية- شراء احتياجات.docx | Actual Expenses / Operational purchases | `finance/api_expenses.py` | `finance/services/actual_expense_service.py` | implemented |
| `#U0633#U062f#U0627#U062f #U0645#U0633#U062a#U062d#U0642#U0627#U062a #U0627#U0644#U0645#U0648#U0631#U062f.docx` | سداد مستحقات المورد.docx | Supplier Settlement | `finance/api_supplier_settlement.py` | `finance/services/supplier_settlement_service.py` | implemented |
| `#U0637#U0644#U0628 #U0639#U0647#U062f#U0629 #U0646#U0642#U062f#U064a#U0629.docx` | طلب عهدة نقدية.docx | Petty Cash | `finance/api_petty_cash.py` | `finance/services/petty_cash_service.py` | implemented |
| `#U0642#U064a#U0648#U062f #U064a#U0648#U0645#U064a#U0629.docx` | قيود يومية.docx | Manual Ledger / Fiscal lifecycle | `finance/api_ledger.py`, `finance/api_fiscal.py` | `finance/services/ledger_approval_service.py`, `finance/services/fiscal_governance_service.py` | implemented |
| `#U200f#U200f#U0627#U0644#U0646#U0641#U0642#U0627#U062a #U0627#U0644#U062a#U0634#U063a#U064a#U0644#U064a#U0629 - #U0627#U0644#U0635#U064a#U0627#U0646#U0629.docx` | النفقات التشغيلية - الصيانة.docx | Actual Expenses / Maintenance | `finance/api_expenses.py` | `finance/services/actual_expense_service.py` | implemented |
| `#U200f#U200f#U0627#U0644#U0646#U0641#U0642#U0627#U062a #U0627#U0644#U062a#U0634#U063a#U064a#U0644#U064a#U0629 - #U0627#U0644#U0645#U062d#U0631#U0648#U0642#U0627#U062a.docx` | النفقات التشغيلية - المحروقات.docx | Fuel Reconciliation + Actual Expenses | `core/views/fuel_reconciliation_dashboard.py`, `finance/api_expenses.py` | `core/services/fuel_reconciliation_service.py`, `finance/services/actual_expense_service.py` | implemented with governed posting evidence |
| `#U200f#U200f#U0627#U0644#U0646#U0641#U0642#U0627#U062a #U0627#U0644#U062a#U0634#U063a#U064a#U0644#U064a#U0629 - #U0627#U0644#U0645#U0631#U062a#U0628#U0627#U062a.docx` | النفقات التشغيلية - المرتبات.docx | Labor / Daily execution / Petty cash settlement | `core/services/daily_log_execution.py`, `finance/api_petty_cash.py` | `core/services/daily_log_execution.py`, `finance/services/petty_cash_service.py` | implemented with shadow accounting |
| `#U200f#U200f#U0627#U0644#U0646#U0641#U0642#U0627#U062a #U0627#U0644#U062a#U0634#U063a#U064a#U0644#U064a#U0629 - #U0633#U062f#U0627#U062f #U0627#U0644#U0643#U0647#U0631#U0628#U0627#U0621 #U0648#U063a#U064a#U0631#U0647.docx` | النفقات التشغيلية - سداد الكهرباء وغيره.docx | Actual Expenses / Utilities | `finance/api_expenses.py` | `finance/services/actual_expense_service.py` | implemented |
| `#U200f#U200f#U0627#U0644#U0646#U0641#U0642#U0627#U062a #U0627#U0644#U062a#U0634#U063a#U064a#U0644#U064a#U0629 - 5.docx` | النفقات التشغيلية - 5.docx | Actual Expenses / Miscellaneous operational expense | `finance/api_expenses.py` | `finance/services/actual_expense_service.py` | implemented |
| `#U200f#U200f#U200f#U200f#U200f#U200fMicrosoft Visio Drawing #U062c#U062f#U064a#U062f - #U0645#U062e#U0637#U0637 #U0627#U0644#U0627#U0634#U062c#U0627#U0631 #U0627#U0644#U0645#U0639#U0645#U0631#U0629.vsdx` | Microsoft Visio Drawing جديد - مخطط الاشجار المعمرة.vsdx | Perennial / biological assets flow | `core/api/viewsets/crop.py` | `core/services/daily_log_execution.py` | implemented operationally |
| `#U200f#U200f#U200f#U200fMicrosoft Visio Drawing #U062c#U062f#U064a#U062f - #U0645#U062e#U0637#U0637 #U0627#U0644#U0637#U0648#U0627#U0641- #U0646#U0633#U062e#U0629.vsdx` | Microsoft Visio Drawing جديد - مخطط الطواف- نسخة.vsdx | Touring / contract operations flow | `core/services/contract_operations_service.py` | `core/services/contract_operations_service.py` | implemented |
| `#U200f#U200fMicrosoft Visio Drawing #U062c#U062f#U064a#U062f - #U0645#U062e#U0637#U0637 #U0627#U0644#U063a#U0631#U0633.vsdx` | Microsoft Visio Drawing جديد - مخطط الغرس.vsdx | Planting / crop-plan execution flow | `core/api/viewsets/crop.py` | `core/services/daily_log_execution.py` | implemented |
| `Mobile Field App (Sovereign)` | التطبيق الميداني السيادي | Field Evidence / Activity Intake | `mobile_field_app/` + `core/api/viewsets/offline_replay.py` | `core/services/activity_service.py` | Certified 100/100 (Inbox, Vault, AI Clarity, GIS Recon) |
| `Microsoft Visio Drawing #U062c#U062f#U064a#U062f.vsdx` | Microsoft Visio Drawing جديد.vsdx | General documentary-cycle diagram | `docs/doctrine/DOCUMENTARY_CYCLE.md` | `docs/doctrine/STRICT_COMPLETION_MATRIX.md` | reference asset |

## Operational readiness references
- Enterprise runbook: `docs/operations/ENTERPRISE_PRODUCTION_RUNBOOK_V4.md`
- Backup/restore runbook: `docs/operations/BACKUP_RESTORE_RUNBOOK_V4.md`

---

## V6 extensions

| الدورة | الكيان/الواجهة | الخدمة / العقد | الأثر الرقابي |
|---|---|---|---|
| العهدة النقدية | Finance/PettyCashDashboard | `petty_cash_service.py` | idempotency + audit |
| تسوية الموردين | Finance/SupplierSettlementDashboard | `supplier_settlement_service.py` | approval + settlement audit |
| المصروفات الفعلية | Finance/ActualExpenseList | `actual_expense_service.py` | maker/checker + delete via service |
| الأصول الثابتة | FixedAssetsDashboard | `fixed_asset_workflow_service.py` | lifecycle + audit trail |
| المحروقات | FuelReconciliationDashboard | `fuel_reconciliation_service.py` | expected vs actual + reconciliation |
| الانحرافات التخطيطية | PredictiveVariance / VarianceAnalysis | `schedule_variance_service.py` | variance classification |
| التسوية الموسمية | تقارير/خدمات الإقفال | `seasonal_settlement_service.py` | closing evidence |
| التدقيق الحساس | Audit pages | `audit_event_factory.py`, `sensitive_audit.py` | forensic chain |
| التوسعة متعددة المواقع | scope / farm/site/sector context | `multi_site_policy_service.py` | scope traceability |
| التقارير التنفيذية العربية | Executive Arabic Dashboard | `enterpriseArabicConfig.js` + `ArabicExecutiveKpiCards.jsx` | role-aware Arabic reporting |

## V8 extensions

| الدورة | الكيان/الواجهة | الخدمة / العقد | الأثر الرقابي |
|---|---|---|---|
| التكاملات المالية الخارجية | `integrations/api.py` | `integrations/services.py` | service-layer only + idempotency |
| الحوكمة المالية المؤسسية | `finance/api_ledger.py`, `finance/api_fiscal.py` | `finance/services/fiscal_fund_governance_service.py` | close/post/reverse policy |
| امتثال الحصاد | `core/services/harvest_service.py` | `core/services/harvest_compliance_service.py` | attachment + location + crop plan policy |
| التسوية الموسمية | تقارير/خدمات الإقفال | `core/services/seasonal_settlement_service.py` | WIP->close policy |
| تسوية المشاركة | harvest/sharecropping flows | `core/services/sharecropping_settlement_service.py` | normalized share settlement |
| الزكاة/السيادي | harvest + reports | `core/services/sovereign_zakat_service.py` | enterprise disclosure wrapper |
| مستويات المزارع | settings/runtime policy | `core/services/farm_tiering_policy_service.py` | runtime tier behavior |


## V10 extensions

| الدورة | الكيان/الواجهة | الخدمة / العقد | الأثر المؤسسي |
|---|---|---|---|
| جاهزية التخطيط المؤسسي | Planning dashboards / closeout | `core/services/planning_enterprise_service.py` | seasonal close + harvest readiness + tiered approvals |
| الجاهزية المالية المؤسسية | finance closing / disclosure | `finance/services/enterprise_financial_readiness_service.py` | fiscal close pack + share settlement + zakat disclosure |
| عقد Smart Card القياسي | V21 Daily Execution UI | `core/services/smart_card_stack_service.py` | `test_smart_card_stack_contract.py` ensures 11-field compliance + SIMPLE/STRICT |

## V21 Phase 2 extensions

| الدورة | الكيان/الواجهة | الخدمة / العقد | الأثر المؤسسي |
|---|---|---|---|
| الحوكمة القطاعية | Sector Lanes / Workbench | `finance/tests/test_sector_lanes.py` | 5 rigid sector lanes + FFM aggregation |
| ضوابط المزارع | SMALL / MEDIUM / LARGE | `core/tests/test_farm_size_governance.py` | explicit validation of FFM presence |
| الأثر الجنائي للتشغيل | Forensic Approval Timeline | `finance/tests/test_forensic_approval_timeline.py` | immutable `ApprovalStageEvent` timeline |
| فصل مسؤولية المنشئ | Creator Block / Exceptions | `finance/tests/test_single_role_collapse.py` | maker-checker absolute block |

## V21 Phase 3 extensions

| الدورة | الكيان/الواجهة | الخدمة / العقد | الأثر المؤسسي |
|---|---|---|---|
| إغلاق منافذ الرصد | Finance Route Blocks | `finance/tests/test_simple_mode_finance_block.py` | SIMPLE mode blocks explicit ledger writes |
| حوكمة التسريب المالي | Route Leakage & Breach | `core/tests/test_route_breach_middleware.py` | Admin-proof `ROUTE_BREACH_SIMPLE_MODE` + AuditLog |
| الحسابات الظلية | Shadow Accounting | `core/tests/test_shadow_accounting_strict.py` | Invisible SIMPLE ledger traces mapped strictly |
| سياسة العرض الجبرية | No Absolute Amounts Sync | `core/tests/test_simple_no_finance_leak.py` | Prevents absolute leaks defaulting to `cost_visibility` settings |


## V10 merged enhancements

This V10 matrix keeps the V9 business/ERP mapping as the source of truth and backports the following readiness/testing assets from V99:

- `backend/smart_agri/core/tests/test_daily_log_governance_api.py`
- `backend/smart_agri/core/tests/test_activity_cost_snapshot_integrity.py`
- `frontend/src/components/daily-log/__tests__/ActivityItemsField.test.jsx`
- `frontend/src/pages/__tests__/DailyLogHistory.test.jsx`
- `docs/reports/READINESS_REPORT_INDEX.md`

## Governance note

- Business logic authority remains the V9 services for planning, finance, seasonal settlement, sharecropping, sovereign/zakat, harvest compliance, and farm tiering.
- V99 contributions in V10 are intentionally limited to tests, reporting index, and documentary-clarity improvements.
