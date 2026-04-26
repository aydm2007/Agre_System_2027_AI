import os
import sys
from pathlib import Path

import psycopg2

REPORT_FILE = Path(__file__).resolve().parent.parent.parent / 'bare_metal_report.txt'


def log(msg):
    with open(REPORT_FILE, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)


def probe():
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write('=== BARE METAL PROBE ===\n')
    log('[1] Python is Alive.')
    log(f'    Version: {sys.version}')
    try:
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME', 'agriasset'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', ''),
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            connect_timeout=3,
        )
        log('✅ Raw Connection SUCCESS.')
        conn.close()
    except Exception as exc:
        log(f'❌ Raw Connection FAILED: {exc}')


if __name__ == '__main__':
    probe()
