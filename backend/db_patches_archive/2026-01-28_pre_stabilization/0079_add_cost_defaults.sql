-- Forensic Audit Remediation: MED-002
-- Add DEFAULT values to cost fields in core_activity to prevent insert failures
-- Date: 2026-01-23
-- Author: Forensic Audit Remediation

BEGIN;

-- Add DEFAULT 0 for cost fields that were missing defaults
ALTER TABLE public.core_activity 
ALTER COLUMN cost_materials SET DEFAULT 0,
ALTER COLUMN cost_labor SET DEFAULT 0,
ALTER COLUMN cost_machinery SET DEFAULT 0;

-- Add documentation comment
COMMENT ON TABLE public.core_activity IS 
'Forensic Audit Fix MED-002: Added DEFAULT 0 for cost_materials, cost_labor, cost_machinery to prevent insert failures when creating activities from code that does not set these values. Added 2026-01-23.';

COMMIT;
