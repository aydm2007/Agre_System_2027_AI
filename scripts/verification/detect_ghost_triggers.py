import os
import sys

import django
from django.db import connection
from django.db.utils import OperationalError, DatabaseError


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../backend')))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
django.setup()


ALLOWED_TRIGGERS = {
    # Forensic append-only expense audit trigger
    "trg_audit_expense",
    # Operational integrity triggers (documented)
    "core_activity_upd_ts",
    "core_dailylog_upd_ts",
    "core_farm_upd_ts",
    "core_harvestlot_upd_ts",
    "core_item_upd_ts",
    "core_location_upd_ts",
    "core_stockmovement_upd_ts",
    "core_locationtreestock_touch_trg",
    "trg_prevent_negative_tree_stock",
    # Financial/treasury immutability controls applied by finance migrations
    "trg_financialledger_immutable",
    "trg_prevent_ledger_mutation",
    "prevent_treasurytransaction_update",
    "prevent_treasurytransaction_delete",
    # Tree stock guard trigger introduced in core migration 0042
    "trg_core_locationtreestock_prevent_negative",
}


def _fetch_triggers():
    vendor = connection.vendor
    with connection.cursor() as cursor:
        if vendor == 'postgresql':
            cursor.execute(
                """
                SELECT trigger_name, event_object_table
                FROM information_schema.triggers
                WHERE trigger_schema = 'public'
                ORDER BY trigger_name
                """
            )
            return cursor.fetchall(), vendor
        if vendor == 'sqlite':
            cursor.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='trigger' ORDER BY name")
            return cursor.fetchall(), vendor
        raise RuntimeError(f'Unsupported database vendor for trigger detection: {vendor}')


def detect_ghost_triggers():
    print("Detecting ghost triggers...")
    try:
        rows, _vendor = _fetch_triggers()
    except (OperationalError, DatabaseError) as exc:
        print(f'BLOCKED: database unavailable for trigger detection: {exc}')
        return 2
    except RuntimeError as exc:
        print(f'BLOCKED: {exc}')
        return 2

    ghosts = set()
    for trigger_name, table_name in rows:
        if trigger_name not in ALLOWED_TRIGGERS:
            ghosts.add((trigger_name, table_name))

    if not ghosts:
        print("OK: No ghost triggers found.")
        return 0

    print("BLOCK: Ghost triggers detected:")
    for trigger_name, table_name in sorted(ghosts):
        print(f"- {trigger_name} on {table_name}")
    return 1


if __name__ == "__main__":
    raise SystemExit(detect_ghost_triggers())
