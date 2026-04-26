import os
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / 'pg_output.txt'


def _conn_params(dbname: str) -> dict:
    password = os.getenv('DB_PASSWORD')
    if not password:
        raise SystemExit('DB_PASSWORD is required for unlock_pg.py')
    return {
        'dbname': dbname,
        'user': os.getenv('DB_USER', 'postgres'),
        'password': password,
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
    }


def main():
    target_db = os.getenv('DB_NAME', 'agriasset')
    admin_db = os.getenv('POSTGRES_ADMIN_DB', 'postgres')
    conn = psycopg2.connect(**_conn_params(admin_db))
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("""
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = %s AND pid <> pg_backend_pid();
    """, (target_db,))
    killed = cur.fetchall()
    conn.close()
    with OUTPUT.open('w', encoding='utf-8') as f:
        f.write(f'Killed {len(killed)} connections to {target_db}.\n')
