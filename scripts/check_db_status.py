import os
import sys
import psycopg2
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
                    env_vars[key] = value
    return env_vars

def check_postgres(user, password, host, port, dbname):
    try:
        conn = psycopg2.connect(
            dbname='postgres', 
            user=user,
            password=password,
            host=host,
            port=port
        )
        conn.close()
        return True, None
    except psycopg2.OperationalError as e:
        return False, str(e)

def main():
    try:
        env = read_env(ENV_FILE)
        user = env.get('DB_USER', 'postgres')
        password = env.get('DB_PASSWORD', 'postgres')
        host = env.get('DB_HOST', 'localhost')
        port = env.get('DB_PORT', '5432')
        dbname = env.get('DB_NAME', 'agriasset')

        success, error = check_postgres(user, password, host, port, dbname)
        
        if success:
            print("DB_CONNECTION_SUCCESS")
        else:
            print(f"DB_CONNECTION_FAILURE: {error}")
    except Exception as e:
        print(f"SCRIPT_ERROR: {e}")

if __name__ == "__main__":
    main()
