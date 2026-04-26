# DOCX → Code Traceability Matrix (V3)

This matrix keeps documentary-cycle assets aligned with implemented code paths, service ownership, and current status.
Historical snapshot only. Prefer `DOCX_CODE_TRACEABILITY_MATRIX_V10.md` for active readiness and closure decisions.

| Docx file | Decoded title | Workflow | API/UI surface | Service owner | Status |
|---|---|---|---|---|---|
| `#U0627#U0644#U0627#U0635#U0648#U0631 #U0627#U0644#U062b#U0627#U0628#U062a#U0629.docx` | الاصور الثابتة.docx | Fixed Assets | `core/views/fixed_assets_dashboard.py` | `core/services/fixed_asset_workflow_service.py` | dashboard/read-model governed, workflow evidence improving |
| `#U0627#U0644#U0627#U064a#U062c#U0627#U0631#U0627#U062a.docx` | الايجارات.docx | Contract Operations / Rentals | `core/services/contract_operations_service.py` | `core/services/contract_operations_service.py` | implemented |
| `#U0627#U0644#U0634#U0631#U0627#U0643 #U0648#U0627#U0644#U0637#U0648#U0627#U0641.docx` | الشراك والطواف.docx | Contract Operations / Sharecropping & Touring | `core/services/contract_operations_service.py` | `core/services/contract_operations_service.py` | implemented |
| `#U0627#U0644#U0645#U0642#U0628#U0648#U0636#U0627#U062a.docx` | المقبوضات.docx | Receipts and Deposit | `finance/api_treasury.py` | `finance/services/treasury_service.py` | implemented |
| `#U0627#U0644#U0646#U0641#U0642#U0627#U062a #U0627#U0644#U062a#U0634#U063a#U064a#U0644#U064a#U0629- #U0634#U0631#U0627#U0621 #U0627#U062d#U062a#U064a#U0627#U062c#U0627#U062a.docx` | النفقات التشغيلية- شراء احتياجات.docx | Actual Expenses / Operational purchases | `finance/api_expenses.py` | `finance/services/actual_expense_service.py` | implemented |
| `#U0633#U062f#U0627#U062f #U0645#U0633#U062a#U062d#U0642#U0627#U062a #U0627#U0644#U0645#U0648#U0631#U062f.docx` | سداد مستحقات المورد.docx | Supplier Settlement | `finance/api_supplier_settlement.py` | `finance/services/supplier_settlement_service.py` | implemented |
| `#U0637#U0644#U0628 #U0639#U0647#U062f#U0629 #U0646#U0642#U062f#U064a#U0629.docx` | طلب عهدة نقدية.docx | Petty Cash | `finance/api_petty_cash.py` | `finance/services/petty_cash_service.py` | implemented |
| `#U0642#U064a#U0648#U062f #U064a#U0648#U0645#U064a#U0629.docx` | قيود يومية.docx | Manual Ledger / Fiscal lifecycle | `finance/api_ledger.py`, `finance/api_fiscal.py` | `finance/services/ledger_approval_service.py`, `finance/services/fiscal_governance_service.py` | implemented |
| `#U200f#U200f#U0627#U0644#U0646#U0641#U0642#U0627#U062a #U0627#U0644#U062a#U0634#U063a#U064a#U0644#U064a#U0629 - #U0627#U0644#U0635#U064a#U0627#U0646#U0629.docx` | ‏‏النفقات التشغيلية - الصيانة.docx | Actual Expenses / Maintenance | `finance/api_expenses.py` | `finance/services/actual_expense_service.py` | implemented |
| `#U200f#U200f#U0627#U0644#U0646#U0641#U0642#U0627#U062a #U0627#U0644#U062a#U0634#U063a#U064a#U0644#U064a#U0629 - #U0627#U0644#U0645#U062d#U0631#U0648#U0642#U0627#U062a.docx` | ‏‏النفقات التشغيلية - المحروقات.docx | Fuel Reconciliation + Actual Expenses | `core/views/fuel_reconciliation_dashboard.py`, `finance/api_expenses.py` | `core/services/fuel_reconciliation_service.py`, `finance/services/actual_expense_service.py` | partial workflow; read model governed |
| `#U200f#U200f#U0627#U0644#U0646#U0641#U0642#U0627#U062a #U0627#U0644#U062a#U0634#U063a#U064a#U0644#U064a#U0629 - #U0627#U0644#U0645#U0631#U062a#U0628#U0627#U062a.docx` | ‏‏النفقات التشغيلية - المرتبات.docx | Labor / Daily execution / Petty cash settlement | `core/services/daily_log_execution.py`, `finance/api_petty_cash.py` | `core/services/daily_log_execution.py`, `finance/services/petty_cash_service.py` | implemented with shadow accounting |
| `#U200f#U200f#U0627#U0644#U0646#U0641#U0642#U0627#U062a #U0627#U0644#U062a#U0634#U063a#U064a#U0644#U064a#U0629 - #U0633#U062f#U0627#U062f #U0627#U0644#U0643#U0647#U0631#U0628#U0627#U0621 #U0648#U063a#U064a#U0631#U0647.docx` | ‏‏النفقات التشغيلية - سداد الكهرباء وغيره.docx | Actual Expenses / Utilities | `finance/api_expenses.py` | `finance/services/actual_expense_service.py` | implemented |
| `#U200f#U200f#U0627#U0644#U0646#U0641#U0642#U0627#U062a #U0627#U0644#U062a#U0634#U063a#U064a#U0644#U064a#U0629 - 5.docx` | ‏‏النفقات التشغيلية - 5.docx | Actual Expenses / Miscellaneous operational expense | `finance/api_expenses.py` | `finance/services/actual_expense_service.py` | implemented |
| `#U200f#U200f#U200f#U200f#U200f#U200fMicrosoft Visio Drawing #U062c#U062f#U064a#U062f - #U0645#U062e#U0637#U0637 #U0627#U0644#U0627#U0634#U062c#U0627#U0631 #U0627#U0644#U0645#U0639#U0645#U0631#U0629.vsdx` | ‏‏‏‏‏‏Microsoft Visio Drawing جديد - مخطط الاشجار المعمرة.vsdx | Perennial / biological assets flow | `core/api/viewsets/crop.py` | `core/services/daily_log_execution.py` | implemented operationally |
| `#U200f#U200f#U200f#U200fMicrosoft Visio Drawing #U062c#U062f#U064a#U062f - #U0645#U062e#U0637#U0637 #U0627#U0644#U0637#U0648#U0627#U0641- #U0646#U0633#U062e#U0629.vsdx` | ‏‏‏‏Microsoft Visio Drawing جديد - مخطط الطواف- نسخة.vsdx | Touring / contract operations flow | `core/services/contract_operations_service.py` | `core/services/contract_operations_service.py` | implemented |
| `#U200f#U200fMicrosoft Visio Drawing #U062c#U062f#U064a#U062f - #U0645#U062e#U0637#U0637 #U0627#U0644#U063a#U0631#U0633.vsdx` | ‏‏Microsoft Visio Drawing جديد - مخطط الغرس.vsdx | Planting / crop-plan execution flow | `core/api/viewsets/crop.py` | `core/services/daily_log_execution.py` | implemented |
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
> [!WARNING]
> Historical baseline only. Not active reference.
> Use `docs/doctrine/DOCX_CODE_TRACEABILITY_MATRIX_V10.md` with the V21 active references instead.
