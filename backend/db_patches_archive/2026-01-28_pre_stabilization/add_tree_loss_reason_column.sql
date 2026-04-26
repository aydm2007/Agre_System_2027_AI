-- Patch: add tree_loss_reason_id column to legacy databases
-- Usage:
--   1. Connect to the target PostgreSQL database (e.g. via pgAdmin 4).
--   2. Execute this script.
--   3. Afterwards run `python manage.py migrate` to let Django record the migration state.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'core_activity'
          AND column_name = 'tree_loss_reason_id'
    ) THEN
        ALTER TABLE public.core_activity
            ADD COLUMN tree_loss_reason_id BIGINT NULL;

        ALTER TABLE public.core_activity
            ADD CONSTRAINT core_activity_tree_loss_reason_id_fk
            FOREIGN KEY (tree_loss_reason_id)
            REFERENCES public.core_treelossreason (id)
            ON DELETE SET NULL
            DEFERRABLE INITIALLY DEFERRED;

        CREATE INDEX IF NOT EXISTS core_activity_tree_loss_reason_id_idx
            ON public.core_activity (tree_loss_reason_id);
    END IF;
END;
$$;
