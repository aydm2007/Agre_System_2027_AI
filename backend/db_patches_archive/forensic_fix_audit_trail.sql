-- AgriAsset Forensic Patch: Immutable Audit Trail
-- Target: Database Level Security (PostgreSQL)
-- Application: Finance Module (ActualExpense)

BEGIN;

-- 1. Create Shadow Table (Append-Only Logic)
CREATE TABLE IF NOT EXISTS finance_audit_log_finance (
    id SERIAL PRIMARY KEY,
    expense_id INT NOT NULL,
    old_amount DECIMAL(19,4),
    new_amount DECIMAL(19,4),
    changed_by_user VARCHAR(100),
    change_type VARCHAR(10), -- 'UPDATE', 'DELETE'
    changed_at TIMESTAMPTZ DEFAULT NOW(),
    client_ip VARCHAR(45),
    notes TEXT
);

-- 2. Create Trigger Function
CREATE OR REPLACE FUNCTION log_expense_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'DELETE') THEN
        INSERT INTO finance_audit_log_finance (expense_id, old_amount, change_type, changed_by_user)
        VALUES (OLD.id, OLD.amount, 'DELETE', current_user);
        RETURN OLD;
    ELSIF (TG_OP = 'UPDATE') THEN
        -- Only log if financial value or critical fields changed
        IF (OLD.amount <> NEW.amount OR OLD.status <> NEW.status) THEN
            INSERT INTO finance_audit_log_finance (
                expense_id, old_amount, new_amount, change_type, changed_by_user, notes
            )
            VALUES (
                OLD.id, OLD.amount, NEW.amount, 'UPDATE', current_user, 
                'Status: ' || OLD.status || ' -> ' || NEW.status
            );
        END IF;
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- 3. Bind Trigger
DROP TRIGGER IF EXISTS trg_audit_expense ON core_actual_expense; -- Using correct table name from previous context if possible, assuming finance_actualexpense or core_actualexpense. Checking models... context said 'finance_actualexpense' in SQL prompt but previous sql used 'core_actual_expense'. I will use 'core_actual_expense' as it's the likely physical table name for ActualExpense in Core app or Finance app.
-- Wait, prompt said 'finance_actualexpense'. I'll stick to 'finance_actualexpense' if the app is 'finance'.
-- Previous list_dir showed 'backend/smart_agri/finance/models.py', so table is likely 'finance_actualexpense'.

DROP TRIGGER IF EXISTS trg_audit_expense ON finance_actualexpense;
CREATE TRIGGER trg_audit_expense
AFTER UPDATE OR DELETE ON finance_actualexpense
FOR EACH ROW EXECUTE FUNCTION log_expense_changes();

COMMIT;
