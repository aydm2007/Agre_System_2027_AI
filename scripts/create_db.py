import os
import sys

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


def create_database():
    db_user = os.getenv('DB_USER', 'postgres')
    db_pass = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_name = os.getenv('DB_NAME', 'agriasset')
    if not db_pass:
        raise SystemExit('DB_PASSWORD is required for create_db.py')
    try:
        con = psycopg2.connect(dbname='postgres', user=db_user, password=db_pass, host=db_host)
        con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = con.cursor()
        cur.execute('SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s', (db_name,))
        if not cur.fetchone():
            cur.execute(f'CREATE DATABASE "{db_name}"')
        cur.close(); con.close()
    except Exception as exc:
        print(f'❌ Failed to create database: {exc}')
        sys.exit(1)


if __name__ == '__main__':
    create_database()
