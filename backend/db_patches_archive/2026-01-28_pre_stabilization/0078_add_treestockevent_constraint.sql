-- Forensic Audit Remediation: HIGH-001
-- Add CHECK constraint to prevent negative resulting_tree_count in tree stock events
-- Date: 2026-01-23
-- Author: Forensic Audit Remediation

BEGIN;

-- Add CHECK constraint for resulting_tree_count (must be >= 0 or NULL)
ALTER TABLE public.core_treestockevent 
ADD CONSTRAINT treestockevent_resulting_count_non_negative
CHECK (resulting_tree_count IS NULL OR resulting_tree_count >= 0);

-- Add documentation comment
COMMENT ON CONSTRAINT treestockevent_resulting_count_non_negative 
ON public.core_treestockevent IS 
'Forensic Audit Fix HIGH-001: Prevent recording tree stock events with negative resulting counts. Added 2026-01-23.';

COMMIT;
