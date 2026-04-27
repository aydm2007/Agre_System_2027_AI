from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0029_alter_item_uom_alter_iteminventory_uom"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE inventory_purchaseorder
              ADD COLUMN IF NOT EXISTS technical_signature_id integer NULL,
              ADD COLUMN IF NOT EXISTS financial_signature_id integer NULL,
              ADD COLUMN IF NOT EXISTS director_signature_id integer NULL;

            CREATE INDEX IF NOT EXISTS inventory_purchaseorder_technical_signature_id_idx
              ON inventory_purchaseorder (technical_signature_id);
            CREATE INDEX IF NOT EXISTS inventory_purchaseorder_financial_signature_id_idx
              ON inventory_purchaseorder (financial_signature_id);
            CREATE INDEX IF NOT EXISTS inventory_purchaseorder_director_signature_id_idx
              ON inventory_purchaseorder (director_signature_id);

            DO $$
            BEGIN
              IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'inventory_purchaseorder_technical_signature_id_fk'
              ) THEN
                ALTER TABLE inventory_purchaseorder
                  ADD CONSTRAINT inventory_purchaseorder_technical_signature_id_fk
                  FOREIGN KEY (technical_signature_id)
                  REFERENCES auth_user(id)
                  DEFERRABLE INITIALLY DEFERRED;
              END IF;

              IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'inventory_purchaseorder_financial_signature_id_fk'
              ) THEN
                ALTER TABLE inventory_purchaseorder
                  ADD CONSTRAINT inventory_purchaseorder_financial_signature_id_fk
                  FOREIGN KEY (financial_signature_id)
                  REFERENCES auth_user(id)
                  DEFERRABLE INITIALLY DEFERRED;
              END IF;

              IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'inventory_purchaseorder_director_signature_id_fk'
              ) THEN
                ALTER TABLE inventory_purchaseorder
                  ADD CONSTRAINT inventory_purchaseorder_director_signature_id_fk
                  FOREIGN KEY (director_signature_id)
                  REFERENCES auth_user(id)
                  DEFERRABLE INITIALLY DEFERRED;
              END IF;
            END
            $$;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
