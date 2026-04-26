-- Forensic Audit Phase 5: Hardening
-- Round 11 & 15: Immutable Ledger Trigger

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

DROP TRIGGER IF EXISTS trg_immutable_ledger ON core_financial_ledger;

CREATE TRIGGER trg_immutable_ledger
BEFORE UPDATE OR DELETE ON core_financial_ledger
FOR EACH ROW EXECUTE FUNCTION protect_ledger();
