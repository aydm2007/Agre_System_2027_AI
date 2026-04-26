-- AgriAsset Forensic Patch: Network Resilience
-- Target: workspace_v3.1.1.8.8.9.sql application
-- Applied by: Agri-Guardian Agent

BEGIN;

-- 1. Secure Finance Table (ActualExpense)
-- Adding idempotency_key to prevent double-spending due to flaky network
ALTER TABLE core_actual_expense 
ADD COLUMN IF NOT EXISTS idempotency_key UUID;

CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_finance_expense_idempotency 
ON core_actual_expense (idempotency_key) 
WHERE idempotency_key IS NOT NULL;

-- 2. Secure Daily Logs (Critical for Payroll)
-- Adding mobile_request_id to track unique submissions from frontend
ALTER TABLE core_dailylog 
ADD COLUMN IF NOT EXISTS mobile_request_id VARCHAR(64);

CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_dailylog_mobile_req
ON core_dailylog (mobile_request_id)
WHERE mobile_request_id IS NOT NULL;

COMMIT;
