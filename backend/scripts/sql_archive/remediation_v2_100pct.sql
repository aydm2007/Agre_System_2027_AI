-- REMEDIATION V2: 100% INTEGRITY HARDENING
-- Purpose: Resolve "Strict Costing" paradox and finalize ledger immutability.

BEGIN;

-- 1. Enforce Strict Costing (Gap 1.1)
-- Dropping defaults ensures that if Python logic fails to calculate costs, 
-- the DB will reject the transaction instead of recording silent $0 values.
ALTER TABLE public.core_activity ALTER COLUMN cost_materials DROP DEFAULT;
ALTER TABLE public.core_activity ALTER COLUMN cost_labor DROP DEFAULT;
ALTER TABLE public.core_activity ALTER COLUMN cost_machinery DROP DEFAULT;
ALTER TABLE public.core_activity ALTER COLUMN cost_overhead DROP DEFAULT;
ALTER TABLE public.core_activity ALTER COLUMN cost_total DROP DEFAULT;

-- 2. Finalize Financial Ledger Immutability
-- Ensure the protect_ledger function and trigger are active on the latest schema.
CREATE OR REPLACE FUNCTION protect_ledger()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION 'Forensic Integrity Error: Financial Ledger is Immutable. Cannot UPDATE records.';
    ELSIF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Forensic Integrity Error: Financial Ledger is Immutable. Cannot DELETE records.';
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_immutable_ledger ON core_financialledger;

CREATE TRIGGER trg_immutable_ledger
BEFORE UPDATE OR DELETE ON core_financialledger
FOR EACH ROW EXECUTE FUNCTION protect_ledger();

-- 3. Audit Trails
COMMENT ON TABLE public.core_activity IS 'Harden Audit Round 2: Strict Costing Enforced (No Defaults).';
COMMENT ON TABLE public.core_financialledger IS 'Strict Audit Round 2: Absolute Immutability Enforced via Triggers.';

COMMIT;
