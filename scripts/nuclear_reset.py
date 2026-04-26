import os
import sys

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASS = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_NAME = os.getenv('DB_NAME', 'agriasset')


def nuclear_reset():
    if not DB_PASS:
        raise SystemExit('DB_PASSWORD is required for nuclear_reset.py')
    try:
        con = psycopg2.connect(dbname='postgres', user=DB_USER, password=DB_PASS, host=DB_HOST)
        con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = con.cursor()
        cur.execute("""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = %s AND pid <> pg_backend_pid();
        """, (DB_NAME,))
        cur.execute(f'DROP DATABASE IF EXISTS "{DB_NAME}"')
        cur.execute(f'CREATE DATABASE "{DB_NAME}"')
        cur.close(); con.close()
    except Exception as exc:
        print(f'❌ NUCLEAR RESET FAILED: {exc}')
        sys.exit(1)


if __name__ == '__main__':
    nuclear_reset()
