"""
TI-06: Live RLS Verification Script
=====================================
Verifies Row-Level Security is enabled on all tenant transactional tables
by running against a live PostgreSQL connection.

Usage:
    python scripts/verification/verify_rls_live.py

Environment:
    DATABASE_URL — Django-style DB URL  (or uses PGHOST/PGUSER/etc.)
"""
from __future__ import annotations

import os
import sys

# Tables that MUST have RLS enabled for tenant isolation
TENANT_TABLES = [
    "core_farm",
    "core_dailylog",
    "core_activity",
    "core_cropplan",
    "core_cropplanphase",
    "core_financialledger",
    "core_treasurytransaction",
    "core_attachment",
    "core_inventorybucket",
    "core_inventorytransaction",
]

# Tables where RLS is desirable but not immediately critical
ADVISORY_TABLES = [
    "core_pettycash",
    "core_location",
    "core_asset",
    "core_employee",
    "core_warehouseitem",
]


def verify_rls(conn):
    cur = conn.cursor()
    failures = []
    warnings = []

    print("═" * 60)
    print("  AgriAsset V21 — Live RLS Verification")
    print("═" * 60)

    for table in TENANT_TABLES:
        cur.execute(
            """
            SELECT relrowsecurity, relname
            FROM pg_class
            WHERE relname = %s AND relkind = 'r'
            """,
            (table,),
        )
        row = cur.fetchone()
        if not row:
            failures.append(f"Table '{table}' does not exist in the database!")
        elif not row[0]:
            failures.append(f"RLS NOT enabled on critical table: {table}")
        else:
            print(f"  ✅ RLS ENABLED:  {table}")

    for table in ADVISORY_TABLES:
        cur.execute(
            """
            SELECT relrowsecurity, relname
            FROM pg_class
            WHERE relname = %s AND relkind = 'r'
            """,
            (table,),
        )
        row = cur.fetchone()
        if row and not row[0]:
            warnings.append(f"RLS not enabled on advisory table: {table}")
        elif row:
            print(f"  ✅ RLS ENABLED:  {table} (advisory)")

    cur.close()

    print()
    if warnings:
        print("WARNINGS:")
        for w in warnings:
            print(f"  ⚠️  {w}")
        print()

    if failures:
        print("FAILURES:")
        for f in failures:
            print(f"  ❌ {f}")
        print()
        print("RESULT: FAIL ─ RLS not enabled on one or more critical tables.")
        sys.exit(1)

    print("RESULT: PASS ─ All critical tenant tables have RLS enabled.")


def build_connection():
    """Build a psycopg2 connection from environment variables."""
    try:
        import psycopg2
    except ImportError:
        print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary")
        sys.exit(1)

    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        return psycopg2.connect(dsn=database_url)

    # Fallback: standard PG env vars
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "localhost"),
        dbname=os.environ.get("PGDATABASE", "agriasset"),
        user=os.environ.get("PGUSER", "postgres"),
        password=os.environ.get("PGPASSWORD", ""),
        port=int(os.environ.get("PGPORT", "5432")),
    )


if __name__ == "__main__":
    conn = build_connection()
    try:
        verify_rls(conn)
    finally:
        conn.close()
