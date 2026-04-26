# Khameesiya Dual-Mode UAT

- Farm: `الخميسية` / `al-khameesiya`
- Generated: `2026-03-27T12:03:45.205674+00:00`
- Overall Status: `PASS`
- Strict Summary Score: `100.0` / 100

## Before Execution

- canonical_axes: `100`
- release_frozen_baseline: `97`
- farm_provisioning: `0`
- seasonal_cycle: `0`
- mango_cycle: `0`
- banana_cycle: `0`
- inventory_procurement: `0`
- strict_finance: `0`
- harvest_sales: `0`
- frontend_dual_mode: `0`
- end_to_end_new_tenant: `12`

## Phases

### simple_bootstrap_validation
- Status: `PASS`
- Category: `governance_reference_defect`
- Result: `{"mode": "SIMPLE", "cost_visibility": "summarized_amounts", "smart_card_contract": true, "service_card_keys": ["execution", "materials", "labor", "well", "machinery", "fuel", "perennial", "harvest", "control", "variance", "financial_trace"]}`

### seasonal_tomato_cycle
- Status: `PASS`
- Category: `service_layer_defect`
- Result: `{"daily_log_id": 256, "activity_id": 241, "variance_status": "CRITICAL", "smart_card_keys": ["execution", "materials", "machinery", "fuel", "control", "variance", "financial_trace"]}`

### mango_perennial_cycle
- Status: `PASS`
- Category: `service_layer_defect`
- Result: `{"daily_log_id": 257, "activity_id": 242, "tree_delta": -5, "current_tree_count": 500, "tree_loss_reason": "جفاف طبيعي"}`

### banana_perennial_cycle
- Status: `PASS`
- Category: `service_layer_defect`
- Result: `{"daily_log_id": 258, "activity_id": 243, "variety": "جراند نين", "service_rows": 1}`

### inventory_procurement
- Status: `PASS`
- Category: `service_layer_defect`
- Result: `{"purchase_order_id": 28, "receipt_movement_id": "278", "issue_movement_id": "279", "remaining_qty": "6900.000"}`

### simple_posture_only_finance
- Status: `PASS`
- Category: `governance_reference_defect`
- Result: `{"petty_cash_blocked": true, "supplier_settlement_blocked": true, "petty_cash_message": "🔴 [FORENSIC BLOCK] هذه العملية المالية تتطلب تفعيل النظام المالي الصارم (STRICT). المزرعة حالياً في وضع SIMPLE.", "supplier_message": "🔴 [FORENSIC BLOCK] Service execution blocked: STRICT mode required."}`

### strict_mode_transition
- Status: `PASS`
- Category: `api_contract_defect`
- Result: `{"mode": "STRICT", "contract_mode": "full_erp", "treasury_visibility": "visible", "smart_card_count": 7}`

### strict_finance_execution
- Status: `PASS`
- Category: `service_layer_defect`
- Result: `{"petty_cash_request_id": 32, "petty_cash_settlement_id": 20, "supplier_settlement_id": 27, "receipt_status": "COLLECTED", "deposit_status": "DEPOSITED", "reconcile_status": "RECONCILED", "fixed_asset_status": "posted", "fuel_status": "posted"}`

### harvest_and_sales
- Status: `PASS`
- Category: `service_layer_defect`
- Result: `{"harvest_activity_id": 244, "harvest_lot_id": 28, "invoice_id": 23, "invoice_status": "draft"}`

### contract_operations
- Status: `PASS`
- Category: `governance_reference_defect`
- Result: `{"contract_id": 20, "touring_id": 20, "rent_status": "posted", "dashboard_rows": 2}`

### attachments_and_evidence
- Status: `PASS`
- Category: `api_contract_defect`
- Result: `{"operational_scan_state": "passed", "authoritative_archive_state": "hot", "quarantine_state": "quarantined"}`

### governance_workbench
- Status: `PASS`
- Category: `governance_reference_defect`
- Result: `{"approval_request_id": 32, "approval_status": "APPROVED", "stage_events": 7, "workbench_rows": 2, "final_required_role": "SECTOR_DIRECTOR"}`
