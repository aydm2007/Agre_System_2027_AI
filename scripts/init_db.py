import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from pathlib import Path

# Fix encoding for Windows console
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent / 'backend'
ENV_FILE = BASE_DIR / '.env'

def read_env(file_path):
    env_vars = {}
    if file_path.exists():
        with open(file_path, 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    env_vars[key] = value.strip()
    return env_vars

def create_database():
    env = read_env(ENV_FILE)
    
    user = env.get('DB_USER', 'postgres')
    password = env.get('DB_PASSWORD', 'postgres')
    host = env.get('DB_HOST', 'localhost')
    port = env.get('DB_PORT', '5432')
    target_db = env.get('DB_NAME', 'smart_agri_db')

    print(f"🐘 Connecting to Postgres to check database '{target_db}'...")

    try:
        # Connect to default 'postgres' db to perform administrative tasks
        con = psycopg2.connect(
            dbname='postgres',
            user=user,
            password=password,
            host=host,
            port=port
        )
        con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = con.cursor()

        # Check if DB exists
        cur.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (target_db,))
        exists = cur.fetchone()

        if not exists:
            print(f"⚠️ Database '{target_db}' not found. Creating it...")
            cur.execute(f'CREATE DATABASE "{target_db}"')
            print(f"✅ Database '{target_db}' created successfully!")
        else:
            print(f"✅ Database '{target_db}' already exists.")

        cur.close()
        con.close()
        return True

    except psycopg2.OperationalError as e:
        print(f"❌ Connection Failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    if create_database():
        sys.exit(0)
    else:
        sys.exit(1)
