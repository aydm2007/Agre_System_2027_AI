import os
import sys
import psycopg2
from django.conf import settings

# Manual setup to read settings without full django setup
sys.path.append(os.path.join(os.getcwd(), 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')

# Just try a raw socket connect
import socket

def check_db_port(host, port):
    print(f"Testing {host}:{port}...")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    try:
        s.connect((host, int(port)))
        print("✅ Port is Open!")
        s.close()
        return True
    except Exception as e:
        print(f"❌ Port Check Failed: {e}")
        return False

if __name__ == "__main__":
    check_db_port("127.0.0.1", 5432)
