# Sales and HR Deep Validation Report (Phase 9)

This report evaluates the integrity of the Sales module and HR (Labor) recording within the Agre ERP 2027 system, following the 100-point assessment criteria in `AGENTS.md`.

## 1. Sales Module Validation

### Findings

| Category | Status | Details |
| :--- | :--- | :--- |
| **Product Integration** | VALID | Correct linkage between `SalesInvoiceItem` and `Item` model. Backend supports `HarvestLot` linkage for COGS calculation. |
| **Inventory Integrity** | STRICT | `SaleService.check_confirmability` strictly verifies stock availability and locks inventory rows for update during confirmation. |
| **Tax Calculation** | ⚠️ DISCREPANCY | Frontend hardcodes **15% VAT** in UI calculations, while Backend hardcodes **0% Tax**. This leads to visual confusion during draft creation. |
| **Pricing Governance** | 🛡️ SECURE | `SaleService` enforces a `minimum_price` based on Moving Average Cost + Zakat Policy + 5% Safety Margin. Prevents sales below cost. |
| **Batch/Lot Tracking** | PARTIAL | Backend supports `harvest_lot_id`, but the Frontend `SalesForm.jsx` does not yet allow manual lot selection; it defaults to the item level. |
| **Accounting (Ledger)** | STRICT | Double-entry posting for Revenue, Receivable, COGS, and Inventory Asset is correctly implemented. |

### Recommendations (Sales)
1. **Sync Tax Policy**: Align Frontend and Backend on tax rates. If VAT is required (15%), it must be persisted on the backend; otherwise, remove the 15% preview in React.
2. **Lot Selection UI**: Add a "Select Batch" option in `SalesForm.jsx` to allow users to pick specific harvest lots, especially for perennial crops where quality/date varies.

---

## 2. HR & Labor Validation

### Findings

| Category | Status | Details |
| :--- | :--- | :--- |
| **Unit Standardization** | PASS | Labor is recorded in `Surra` (quarter-day increments), which is correctly canonicalized in `ActivityService._normalize_surrah_share`. |
| **Employee Selection** | PASS | Supports both registered employees and casual labor batches (CASUAL_BATCH) for flexible workforce management. |
| **Cost Capitalization** | PASS | Daily rates are correctly fetched from `CostPolicy` or `Employee.shift_rate`. Official employees' labor is recorded without capitalizing to crop cost (central payroll). |
| **Estimation Accuracy** | PASS | `LaborEstimationService` provides accurate previews of required labor based on historical `surrah_count` for specific tasks. |
| **Hierarchy Isolation** | PASS | Scope checks ensure users can only assign employees belonging to the same farm tenant. |

### Recommendations (HR)
1. **Attendance Tracking**: Improve the link between `DailyLog` activities and `Timesheet` approvals to ensure that "Approved" activities automatically mark timesheets as "Primary Evidence" for payroll.

---

## 3. 100-Point Evaluation Summary

| Axis | Score | Justification |
| :--- | :--- | :--- |
| **Sales Integrity** | 85/100 | Strong backend governance, but tax mismatch and lot UI selection need refinement. |
| **HR Accuracy** | 95/100 | Solid unit standardization and cost policy integration. |
| **Financial Ledger Consistency** | 100/100 | Immutable ledger postings for both sales (COGS) and labor costs. |

**Final Phase 9 Score: 93/100**
