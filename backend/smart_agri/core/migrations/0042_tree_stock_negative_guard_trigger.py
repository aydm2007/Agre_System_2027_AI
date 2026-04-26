from django.db import migrations


TRIGGER_SQL = """
DO $$
BEGIN
    IF current_setting('server_version_num', true) IS NOT NULL THEN
        CREATE OR REPLACE FUNCTION public.core_locationtreestock_prevent_negative()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $func$
        BEGIN
            IF NEW.current_tree_count < 0 THEN
                RAISE EXCEPTION 'ERR_NEGATIVE_TREE_STOCK: current_tree_count cannot be negative';
            END IF;
            RETURN NEW;
        END;
        $func$;

        DROP TRIGGER IF EXISTS trg_core_locationtreestock_prevent_negative ON public.core_locationtreestock;

        CREATE TRIGGER trg_core_locationtreestock_prevent_negative
        BEFORE INSERT OR UPDATE ON public.core_locationtreestock
        FOR EACH ROW
        EXECUTE FUNCTION public.core_locationtreestock_prevent_negative();
    END IF;
END
$$;
"""

REVERSE_SQL = """
DO $$
BEGIN
    IF current_setting('server_version_num', true) IS NOT NULL THEN
        DROP TRIGGER IF EXISTS trg_core_locationtreestock_prevent_negative ON public.core_locationtreestock;
        DROP FUNCTION IF EXISTS public.core_locationtreestock_prevent_negative();
    END IF;
END
$$;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0041_auditlog_old_payload_reason"),
    ]

    operations = [
        migrations.RunSQL(sql=TRIGGER_SQL, reverse_sql=REVERSE_SQL),
    ]

