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

def write_env(file_path, env_vars):
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    new_lines = []
    keys_written = set()
    for line in lines:
        if '=' in line and not line.strip().startswith('#'):
            key = line.strip().split('=', 1)[0]
            if key in env_vars:
                new_lines.append(f"{key}={env_vars[key]}\n")
                keys_written.add(key)
                continue
        new_lines.append(line)
    
    # Append new keys
    for key, value in env_vars.items():
        if key not in keys_written:
            new_lines.append(f"{key}={value}\n")
            
    with open(file_path, 'w') as f:
        f.writelines(new_lines)

def check_postgres(user, password, host, port, dbname):
    try:
        conn = psycopg2.connect(
            dbname='postgres', # Connect to default DB first to check auth
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
    print("🐘 Checking Database Connection...")
    env = read_env(ENV_FILE)
    
    user = env.get('DB_USER', 'postgres')
    password = env.get('DB_PASSWORD', 'postgres')
    host = env.get('DB_HOST', 'localhost')
    port = env.get('DB_PORT', '5432')
    dbname = env.get('DB_NAME', 'agriasset')

    success, error = check_postgres(user, password, host, port, dbname)
    
    if success:
        print("✅ Database credentials are correct.")
        return

    print(f"❌ Connection Failed: {error}")
    if "password authentication failed" in str(error):
        print(f"\n🔐 Authentication failure for user '{user}'.")
        print("The password in .env is incorrect for your local Postgres.")
        
        new_pass = input(f"👉 Please enter the correct password for user '{user}': ").strip()
        if new_pass:
            env['DB_PASSWORD'] = new_pass
            write_env(ENV_FILE, env)
            print("✅ .env updated with new password.")
            
            # Re-check
            success, error = check_postgres(user, new_pass, host, port, dbname)
            if success:
                print("✅ Connection test PASSED!")
            else:
                print(f"❌ Still failing: {error}")
    else:
        print("⚠️ Unknown database error. Please check your Postgres service.")

if __name__ == "__main__":
    main()
